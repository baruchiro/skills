"""Conversation-facing operations: present a group, record decisions, resume, export."""
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .analyze import DEFAULT_BLUR_THRESHOLD, suggest_keeper, when
from .store import DECISIONS, members_version, now, sha256_file


class UserError(Exception):
    pass


def _group_rows(store, g):
    ids = json.loads(g["members"])
    q = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in store.db.execute(
        f"SELECT * FROM assets WHERE id IN ({q})", ids)}
    return [rows[i] for i in ids if i in rows]


def pending_groups(store, project, kind=None):
    states = store.asset_states(project)
    out = []
    sql = "SELECT * FROM groups WHERE active=1" + (" AND kind=?" if kind else "") + " ORDER BY ord"
    for g in store.db.execute(sql, (kind,) if kind else ()):
        ids = json.loads(g["members"])
        todo = [i for i in ids if not states.get(i, {}).get("reviewed")]
        if todo:
            out.append((g, len(todo)))
    return out


def status(store, project):
    db = store.db
    states = store.asset_states(project)
    ok = [r["id"] for r in db.execute("SELECT id FROM assets WHERE status='ok'")]
    counts = {"keep": 0, "skip": 0, "undecided_reviewed": 0, "unreviewed": 0}
    for i in ok:
        s = states.get(i)
        if not s or not s["reviewed"]:
            counts["unreviewed"] += 1
        elif s["decision"] == "undecided":
            counts["undecided_reviewed"] += 1
        else:
            counts[s["decision"]] += 1
    pend = pending_groups(store, project)
    by_kind = {}
    for g, _ in pend:
        by_kind[g["kind"]] = by_kind.get(g["kind"], 0) + 1
    other = {r["status"]: r["n"] for r in db.execute(
        "SELECT status, COUNT(*) n FROM assets WHERE status!='ok' GROUP BY status")}
    dups = db.execute("SELECT COUNT(*) FROM (SELECT asset_id FROM occurrences GROUP BY asset_id "
                      "HAVING COUNT(*)>1)").fetchone()[0]
    open_p = db.execute("SELECT * FROM presentations WHERE project=? ORDER BY id DESC LIMIT 1",
                        (project,)).fetchone()
    return {"project": project, "assets_ok": len(ok), "decisions": counts,
            "pending_groups": len(pend), "pending_by_kind": by_kind,
            "not_reviewable": other, "assets_with_duplicate_copies": dups,
            "last_presented_group": open_p["group_key"] if open_p else None}


def _sheet(store, rows, labels, path, cell=320):
    cols = min(len(rows), 4)
    nrows = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, nrows * cell), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for n, (r, lab) in enumerate(zip(rows, labels)):
        x, y = (n % cols) * cell, (n // cols) * cell
        try:
            with Image.open(store.dir / r["library_path"]) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((cell - 8, cell - 8))
                sheet.paste(im, (x + 4 + (cell - 8 - im.width) // 2, y + 4 + (cell - 8 - im.height) // 2))
        except Exception:
            d.text((x + 20, y + cell // 2), "unreadable", fill=(255, 80, 80))
        d.rectangle([x + 4, y + 4, x + 40, y + 28], fill=(0, 0, 0))
        d.text((x + 10, y + 10), str(lab), fill=(255, 255, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.jpg")
    sheet.save(tmp, "JPEG", quality=85)
    os.replace(tmp, path)


def present(store, project, kind=None, group_key=None):
    """Show the open group (or next pending one). Idempotent until decided."""
    pend = pending_groups(store, project, kind)
    if group_key:
        g = store.db.execute("SELECT * FROM groups WHERE key=? AND active=1", (group_key,)).fetchone()
        if not g:
            raise UserError(f"no active group {group_key}")
    else:
        if not pend:
            return {"done": True, "status": status(store, project)}
        last = store.db.execute("SELECT group_key FROM presentations WHERE project=? ORDER BY id DESC LIMIT 1",
                                (project,)).fetchone()
        keys = {g["key"]: g for g, _ in pend}
        g = keys[last["group_key"]] if last and last["group_key"] in keys else pend[0][0]
    rows = _group_rows(store, g)
    ids = [r["id"] for r in rows]
    ver = members_version(ids)
    with store.tx():
        pid = store.db.execute(
            "INSERT INTO presentations(ts,project,group_key,members,version) VALUES(?,?,?,?,?)",
            (now(), project, g["key"], json.dumps(ids), ver)).lastrowid
    sheet = store.dir / "cache" / "sheets" / f"{g['key']}-{pid}.jpg"
    _sheet(store, rows, range(1, len(rows) + 1), sheet)
    states = store.asset_states(project)
    keeper = suggest_keeper(rows) if g["kind"] == "similar" else None
    items = []
    for n, r in enumerate(rows, 1):
        s = states.get(r["id"], {"decision": "undecided", "reviewed": False})
        items.append({
            "pos": n, "asset_id": r["id"], "taken": when(r["taken_at"]),
            "size": f"{r['width']}x{r['height']}", "bytes": r["size"],
            "sharpness": round(r["sharpness"] or 0, 1),
            "blurry_suspect": (r["sharpness"] or 0) < DEFAULT_BLUR_THRESHOLD,
            "current": s["decision"] if s["reviewed"] else "unreviewed",
            "suggested": (r["id"] == keeper) if keeper else None,
            "copies": store.db.execute("SELECT COUNT(*) FROM occurrences WHERE asset_id=?",
                                       (r["id"],)).fetchone()[0]})
    why = {"similar": "תמונות דומות מאוד (pHash)", "blurry": "חשד לטשטוש",
           "sequence": "רצף לפי זמן צילום"}[g["kind"]]
    return {"group": g["key"], "kind": g["kind"], "why": why, "version": ver,
            "presentation_id": pid, "contact_sheet": str(sheet), "items": items,
            "groups_pending": len(pend), "note": "הצעות בלבד; שום קובץ לא נמחק או הוזז"}


def _positions(s):
    if not s:
        return []
    out = []
    for part in str(s).replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def decide(store, project, group_key, keep=None, skip=None, undecided=None, rest=None, note=None):
    pres = store.db.execute(
        "SELECT * FROM presentations WHERE project=? AND group_key=? ORDER BY id DESC LIMIT 1",
        (project, group_key)).fetchone()
    if not pres:
        raise UserError("group was not presented in this project; run `next` first")
    g = store.db.execute("SELECT * FROM groups WHERE key=?", (group_key,)).fetchone()
    cur_ids = json.loads(g["members"]) if g else []
    if not g or not g["active"] or members_version(cur_ids) != pres["version"]:
        raise UserError("group changed since it was shown; run `next` again before deciding")
    ids = json.loads(pres["members"])
    chosen = {}
    for dec, spec in (("keep", keep), ("skip", skip), ("undecided", undecided)):
        for p in _positions(spec):
            if not 1 <= p <= len(ids):
                raise UserError(f"position {p} out of range 1..{len(ids)}")
            if p in chosen and chosen[p] != dec:
                raise UserError(f"position {p} given two decisions")
            chosen[p] = dec
    if rest:
        if rest not in DECISIONS:
            raise UserError("rest must be keep|skip|undecided")
        for p in range(1, len(ids) + 1):
            chosen.setdefault(p, rest)
    if not chosen:
        raise UserError("no decisions given")
    store.record_decisions(project, [(ids[p - 1], d) for p, d in sorted(chosen.items())],
                           group_key=group_key, presentation_id=pres["id"], note=note)
    return {"recorded": {str(p): d for p, d in sorted(chosen.items())},
            "left_unreviewed_in_group": [p for p in range(1, len(ids) + 1) if p not in chosen],
            "groups_pending": len(pending_groups(store, project))}


def export_keep(store, project, dest):
    dest = Path(dest).expanduser().resolve()
    for r in store.db.execute("SELECT DISTINCT source_dir FROM batches"):
        sd = Path(r[0])
        if dest == sd or sd in dest.parents or dest in sd.parents:
            raise UserError("export destination overlaps a source download folder")
    if store.dir == dest or store.dir in dest.parents or dest in store.dir.parents:
        raise UserError("export destination overlaps the state dir")
    states = store.asset_states(project)
    keep_ids = sorted(i for i, s in states.items() if s["decision"] == "keep" and s["reviewed"])
    dest.mkdir(parents=True, exist_ok=True)
    entries, copied, present_ok = [], 0, 0
    for aid in keep_ids:
        a = store.db.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone()
        stamp = (a["taken_at"] or "unknown").replace(":", "").replace("-", "").replace("T", "_")
        name = f"{stamp}_{a['sha256'][:8]}{a['ext']}"
        target = dest / name
        if target.exists() and sha256_file(target) == a["sha256"]:
            present_ok += 1
        else:
            tmp = dest / f".{name}.tmp"
            shutil.copyfile(store.dir / a["library_path"], tmp)
            os.replace(tmp, target)
            copied += 1
        origs = [o[0] for o in store.db.execute(
            "SELECT source_path FROM occurrences WHERE asset_id=? ORDER BY id", (aid,))]
        entries.append({"file": name, "sha256": a["sha256"], "taken_at": a["taken_at"],
                        "original_paths": origs})
    keep_names = {e["file"] for e in entries}
    stale = sorted(p.name for p in dest.iterdir()
                   if p.is_file() and not p.name.startswith(".") and p.name not in keep_names
                   and p.name not in ("manifest.json", "upload-list.txt"))
    manifest = {"project": project, "exported_at": now(), "count": len(entries), "files": entries}
    mtxt = json.dumps(manifest, ensure_ascii=False, indent=1)
    (dest / "manifest.json").write_text(mtxt)
    (dest / "upload-list.txt").write_text("\n".join(
        e["file"] for e in sorted(entries, key=lambda e: e["file"])) + ("\n" if entries else ""))
    with store.tx():
        store.db.execute("INSERT INTO export_receipts(ts,project,dest,count,manifest_sha256)"
                         " VALUES(?,?,?,?,?)",
                         (now(), project, str(dest), len(entries),
                          hashlib.sha256(mtxt.encode()).hexdigest()))
    return {"dest": str(dest), "keep_count": len(entries), "copied": copied,
            "already_present": present_ok, "stale_files_not_deleted": stale,
            "google_album": "manual: upload the files in dest (upload-list.txt) in Google Photos yourself"}
