"""Deterministic first-pass analysis. Produces suggestions only; never deletes or decides.

* sharpness: variance of the Laplacian on a grayscale copy scaled to <=512px long side.
* phash: 64-bit DCT perceptual hash (32x32 gray, 8x8 low-frequency block, median threshold).
* similar groups: single-link clusters of assets whose pHash Hamming distance <= threshold.
* blurry: sharpness below threshold.
* sequence: everything else, chunked by capture time so every ok asset is reviewable.
Exact duplicates are already collapsed at intake (same sha256 = one asset, many occurrences).
"""
import json
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps

from .ingest import ANALYSIS_VERSION
from .store import members_version

ALGO = f"a{ANALYSIS_VERSION}"
DEFAULT_PHASH_DISTANCE = 6
DEFAULT_BLUR_THRESHOLD = 50.0
DEFAULT_SEQUENCE_SIZE = 12
MAX_GROUP = 12

_N = 32
_DCT = np.array([[np.cos(np.pi * (2 * x + 1) * u / (2 * _N)) for x in range(_N)]
                 for u in range(_N)])


def load_gray(path, long_side=512):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("L")
        w, h = im.size
        s = long_side / max(w, h)
        if s < 1:
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
        return np.asarray(im, dtype=np.float64)


def sharpness(gray):
    if min(gray.shape) < 3:
        return 0.0
    lap = (-4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1]
           + gray[1:-1, :-2] + gray[1:-1, 2:])
    return float(lap.var())


def phash(gray):
    """Hex 64-bit hash or None for (near) flat images, where a hash is meaningless."""
    if gray.std() < 1.0:
        return None
    im = Image.fromarray(gray.astype(np.uint8)).resize((_N, _N), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float64)
    d = _DCT @ a @ _DCT.T
    low = d[:8, :8].flatten()
    med = np.median(low[1:])
    bits = (low > med).astype(np.uint8)
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return f"{v:016x}"


def analyze_assets(store, force=False):
    db = store.db
    rows = db.execute(
        "SELECT id,library_path FROM assets WHERE status='ok' AND "
        "(analysis_version IS NULL OR analysis_version<?)", (ANALYSIS_VERSION,)
        if not force else (10**9,)).fetchall()
    n = bad = 0
    for r in rows:
        try:
            g = load_gray(store.dir / r["library_path"])
            sh, ph = sharpness(g), phash(g)
            with store.tx():
                db.execute("UPDATE assets SET sharpness=?,phash=?,analysis_version=? WHERE id=?",
                           (sh, ph, ANALYSIS_VERSION, r["id"]))
            n += 1
        except Exception as e:
            bad += 1
            with store.tx():
                db.execute("UPDATE assets SET status='unreadable',status_detail=? WHERE id=?",
                           (f"{type(e).__name__}: {e}"[:200], r["id"]))
    return n, bad


def _hamming_matrix(vals):
    arr = np.array([int(v, 16) for v in vals], dtype=np.uint64)
    out = np.zeros((len(arr), len(arr)), dtype=np.uint8)
    for i in range(len(arr)):
        x = arr ^ arr[i]
        # popcount of uint64 via byte view
        out[i] = np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
    return out


def similar_clusters(items, max_dist):
    """items: [(asset_id, phash_hex)] -> list of clusters (lists of asset_id), size>=2."""
    if len(items) < 2:
        return []
    ids = [i for i, _ in items]
    dist = _hamming_matrix([h for _, h in items])
    parent = list(range(len(ids)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    close = np.argwhere(np.triu(dist <= max_dist, k=1))
    for a, b in close:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    clusters = {}
    for i in range(len(ids)):
        clusters.setdefault(find(i), []).append(ids[i])
    return [c for c in clusters.values() if len(c) >= 2]


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def build_groups(store, phash_distance=DEFAULT_PHASH_DISTANCE,
                 blur_threshold=DEFAULT_BLUR_THRESHOLD, sequence_size=DEFAULT_SEQUENCE_SIZE):
    db = store.db
    assets = db.execute("SELECT id,taken_at,phash,sharpness FROM assets "
                        "WHERE status='ok' AND analysis_version IS NOT NULL").fetchall()
    by_id = {a["id"]: a for a in assets}
    key_time = lambda i: (by_id[i]["taken_at"] or "", i)
    groups = []  # (kind, [ids])
    used = set()
    hashed = [(a["id"], a["phash"]) for a in assets if a["phash"]]
    for cl in similar_clusters(hashed, phash_distance):
        cl = sorted(cl, key=key_time)
        for part in _chunks(cl, MAX_GROUP):
            if len(part) >= 2:
                groups.append(("similar", part))
        used.update(cl)
    blurry = sorted((a["id"] for a in assets if a["sharpness"] is not None
                     and a["sharpness"] < blur_threshold and a["id"] not in used),
                    key=lambda i: by_id[i]["sharpness"])
    for part in _chunks(blurry, MAX_GROUP):
        groups.append(("blurry", part))
    used.update(blurry)
    rest = sorted((a["id"] for a in assets if a["id"] not in used), key=key_time)
    for part in _chunks(rest, sequence_size):
        groups.append(("sequence", part))
    order = {"similar": 0, "blurry": 1, "sequence": 2}
    algo = f"{ALGO}:d{phash_distance}:b{blur_threshold}:s{sequence_size}"
    with store.tx():
        db.execute("UPDATE groups SET active=0")
        for n, (kind, ids) in enumerate(sorted(groups, key=lambda g: (order[g[0]], key_time(g[1][0])))):
            ver = members_version(ids)
            key = f"{kind[:3]}-{ver}"
            db.execute(
                "INSERT INTO groups(key,kind,members,version,algo,active,ord) VALUES(?,?,?,?,?,1,?)"
                " ON CONFLICT(key) DO UPDATE SET active=1,ord=excluded.ord,algo=excluded.algo",
                (key, kind, json.dumps(ids), ver, algo, order[kind] * 1e6 + n))
    return {k: sum(1 for g in groups if g[0] == k) for k in order}


def suggest_keeper(rows, blur_threshold=DEFAULT_BLUR_THRESHOLD):
    """Suggestion only: sharp first, then resolution, then sharpness."""
    def score(r):
        sh = r["sharpness"] or 0.0
        return (sh >= blur_threshold, (r["width"] or 0) * (r["height"] or 0), sh)
    return max(rows, key=score)["id"]


def when(taken_at):
    try:
        return datetime.fromisoformat(taken_at).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return taken_at
