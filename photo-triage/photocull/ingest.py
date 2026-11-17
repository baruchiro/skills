"""Local intake adapter: scan a download folder, read EXIF/time, hash, dedupe.

Source files are only ever read. Each new byte-content is copied once into the
content-addressed library (state/library/ab/<sha256>.<ext>); everything after
that works on the copy, so the download folder can be removed afterwards.
"""
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .store import now, sha256_file

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
UNSUPPORTED_IMAGE_EXT = {".heic", ".heif", ".avif", ".dng", ".cr2", ".nef", ".arw"}
ANALYSIS_VERSION = 1


def _is_within(a: Path, b: Path):
    try:
        a.relative_to(b)
        return True
    except ValueError:
        return False


def _fmt_exif(v):
    try:
        return datetime.strptime(str(v).strip()[:19], "%Y:%m:%d %H:%M:%S").isoformat()
    except Exception:
        return None


def _sidecar_time(path: Path):
    for cand in (path.with_name(path.name + ".json"), path.with_suffix(".json")):
        if cand.is_file():
            try:
                ts = json.loads(cand.read_text())["photoTakenTime"]["timestamp"]
                return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(
                    tzinfo=None).isoformat(timespec="seconds")
            except Exception:
                continue
    return None


def read_metadata(path: Path, sidecar_of: Path = None, mtime: float = None):
    """Return dict(width,height,taken_at,taken_src,status,detail). Never raises.

    Time priority: EXIF DateTimeOriginal > sidecar json > EXIF DateTime > file mtime.
    `sidecar_of`/`mtime` refer to the original download file (the library copy has neither).
    """
    from PIL import Image
    out = {"width": None, "height": None, "taken_at": None, "taken_src": None,
           "status": "ok", "detail": None}
    exif_dt = exif_dt2 = None
    try:
        with Image.open(path) as im:
            out["width"], out["height"] = im.size
            ex = im.getexif()
            try:
                sub = ex.get_ifd(0x8769)
            except Exception:
                sub = {}
            exif_dt = _fmt_exif(sub.get(0x9003) or sub.get(0x9004) or "")
            exif_dt2 = _fmt_exif(ex.get(0x0132) or "")
            if ex.get(0x0112) in (5, 6, 7, 8):
                out["width"], out["height"] = out["height"], out["width"]
    except Exception as e:
        out["status"] = "unreadable"
        out["detail"] = f"{type(e).__name__}: {e}"[:200]
    side = _sidecar_time(sidecar_of or path)
    if exif_dt:
        out["taken_at"], out["taken_src"] = exif_dt, "exif"
    elif side:
        out["taken_at"], out["taken_src"] = side, "sidecar"
    elif exif_dt2:
        out["taken_at"], out["taken_src"] = exif_dt2, "exif-modify"
    else:
        m = mtime if mtime is not None else path.stat().st_mtime
        out["taken_at"] = datetime.fromtimestamp(m).isoformat(timespec="seconds")
        out["taken_src"] = "mtime"
    return out


def ingest(store, source_dir):
    src = Path(source_dir).expanduser().resolve()
    if not src.is_dir():
        raise SystemExit(f"source is not a directory: {src}")
    if _is_within(store.dir, src) or _is_within(src, store.dir):
        raise SystemExit("state dir and source dir must not contain each other")
    db = store.db
    with store.tx():
        bid = db.execute("INSERT INTO batches(source_dir,started) VALUES(?,?)",
                         (str(src), now())).lastrowid
    c = dict(files_seen=0, new_assets=0, dup_occurrences=0, unchanged=0, errors=0, other_files=0)
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            p = Path(root) / name
            ext = p.suffix.lower()
            if ext not in IMAGE_EXT and ext not in UNSUPPORTED_IMAGE_EXT:
                c["other_files"] += 1
                continue
            c["files_seen"] += 1
            try:
                _ingest_one(store, bid, p, ext, c)
            except Exception as e:  # one bad file never stops the batch or touches decisions
                c["errors"] += 1
                with store.tx():
                    db.execute("INSERT INTO ingest_errors(batch_id,source_path,error) VALUES(?,?,?)",
                               (bid, str(p), f"{type(e).__name__}: {e}"[:300]))
    with store.tx():
        db.execute("UPDATE batches SET finished=?,files_seen=?,new_assets=?,dup_occurrences=?,"
                   "unchanged=?,errors=?,other_files=? WHERE id=?",
                   (now(), c["files_seen"], c["new_assets"], c["dup_occurrences"],
                    c["unchanged"], c["errors"], c["other_files"], bid))
    c["batch_id"] = bid
    return c


def _ingest_one(store, bid, p: Path, ext, c):
    db = store.db
    st = p.stat()
    sp = str(p)
    cached = db.execute("SELECT * FROM file_cache WHERE source_path=?", (sp,)).fetchone()
    if cached and cached["size"] == st.st_size and cached["mtime_ns"] == st.st_mtime_ns:
        c["unchanged"] += 1
        return
    sha = sha256_file(p)
    row = db.execute("SELECT id FROM assets WHERE sha256=?", (sha,)).fetchone()
    if row:
        aid, new = row["id"], False
    else:
        lib = store.dir / "library" / sha[:2]
        lib.mkdir(parents=True, exist_ok=True)
        dest = lib / f"{sha}{ext}"
        tmp = lib / f".{sha}.tmp"
        shutil.copyfile(p, tmp)  # source is only read
        if sha256_file(tmp) != sha:
            tmp.unlink()
            raise IOError("copy verification failed (file changed while reading?)")
        os.replace(tmp, dest)
        if ext in UNSUPPORTED_IMAGE_EXT:
            meta = {"width": None, "height": None, "status": "unsupported",
                    "detail": f"{ext} needs a codec this tool does not have",
                    "taken_at": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                    "taken_src": "mtime"}
        else:
            meta = read_metadata(dest, sidecar_of=p, mtime=st.st_mtime)
        with store.tx():
            aid = db.execute(
                "INSERT INTO assets(sha256,size,ext,width,height,taken_at,taken_src,status,"
                "status_detail,library_path,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (sha, st.st_size, ext, meta["width"], meta["height"], meta["taken_at"],
                 meta["taken_src"], meta["status"], meta["detail"],
                 str(dest.relative_to(store.dir)), now())).lastrowid
        new = True
    with store.tx():
        if not db.execute("SELECT 1 FROM occurrences WHERE source_path=? AND asset_id=?",
                          (sp, aid)).fetchone():
            db.execute("INSERT INTO occurrences(asset_id,batch_id,source_path,source_mtime_ns)"
                       " VALUES(?,?,?,?)", (aid, bid, sp, st.st_mtime_ns))
        db.execute("INSERT OR REPLACE INTO file_cache VALUES(?,?,?,?)",
                   (sp, st.st_size, st.st_mtime_ns, sha))
    if new:
        c["new_assets"] += 1
    else:
        c["dup_occurrences"] += 1  # same bytes again: provenance kept as another occurrence
