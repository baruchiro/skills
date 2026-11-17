"""Durable SQLite index: assets, occurrences, groups, presentations, decision events.

Design rules (from the approved plan, Picker-specific parts dropped):
* filename is an alias, never a key; identity is sha256 of bytes.
* decisions are append-only events; undo is a corrective event.
* keep/skip/undecided and `reviewed` are separate; reviewed+undecided is valid.
* decisions are per project; skip in one project is not a global verdict.
* one writer at a time (flock); every write is a transaction.
"""
import fcntl
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

SCHEMA_VERSION = 1
DECISIONS = ("keep", "skip", "undecided")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS assets(
  id INTEGER PRIMARY KEY, sha256 TEXT UNIQUE NOT NULL, size INTEGER, ext TEXT,
  width INTEGER, height INTEGER, taken_at TEXT, taken_src TEXT,
  phash TEXT, sharpness REAL, analysis_version INTEGER,
  status TEXT NOT NULL, status_detail TEXT, library_path TEXT, first_seen TEXT);
CREATE TABLE IF NOT EXISTS batches(
  id INTEGER PRIMARY KEY, source_dir TEXT, started TEXT, finished TEXT,
  files_seen INTEGER DEFAULT 0, new_assets INTEGER DEFAULT 0,
  dup_occurrences INTEGER DEFAULT 0, unchanged INTEGER DEFAULT 0,
  errors INTEGER DEFAULT 0, other_files INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS occurrences(
  id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL REFERENCES assets(id),
  batch_id INTEGER, source_path TEXT NOT NULL, source_mtime_ns INTEGER,
  UNIQUE(source_path, asset_id));
CREATE TABLE IF NOT EXISTS file_cache(
  source_path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, sha256 TEXT);
CREATE TABLE IF NOT EXISTS ingest_errors(
  id INTEGER PRIMARY KEY, batch_id INTEGER, source_path TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS groups(
  key TEXT PRIMARY KEY, kind TEXT NOT NULL, members TEXT NOT NULL,
  version TEXT NOT NULL, algo TEXT, active INTEGER DEFAULT 1, ord REAL);
CREATE TABLE IF NOT EXISTS presentations(
  id INTEGER PRIMARY KEY, ts TEXT, project TEXT, group_key TEXT,
  members TEXT NOT NULL, version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY, ts TEXT, project TEXT NOT NULL,
  kind TEXT NOT NULL,            -- decision | undo
  asset_id INTEGER, decision TEXT, reviewed INTEGER,
  group_key TEXT, presentation_id INTEGER, target_event_id INTEGER, note TEXT,
  op_id INTEGER);
CREATE INDEX IF NOT EXISTS ev_proj ON events(project, asset_id);
CREATE TABLE IF NOT EXISTS export_receipts(
  id INTEGER PRIMARY KEY, ts TEXT, project TEXT, dest TEXT, count INTEGER,
  manifest_sha256 TEXT);
"""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class LockedError(RuntimeError):
    pass


class Store:
    def __init__(self, state_dir):
        self.dir = Path(state_dir).expanduser().resolve()
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "library").mkdir(exist_ok=True)
        (self.dir / "cache").mkdir(exist_ok=True)
        self._lockf = open(self.dir / "writer.lock", "w")
        try:
            fcntl.flock(self._lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lockf.close()
            raise LockedError("another photocull process is using this state dir")
        self.db = sqlite3.connect(self.dir / "index.sqlite3", isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        cur = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if cur is None:
            self.db.execute("INSERT INTO meta VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        elif int(cur[0]) > SCHEMA_VERSION:
            raise RuntimeError("index was written by a newer photocull")

    def close(self):
        try:
            self.db.close()
        finally:
            self._lockf.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- transactions -------------------------------------------------
    def tx(self):
        return _Tx(self.db)

    # -- decisions ----------------------------------------------------
    def asset_states(self, project):
        """Replay events -> {asset_id: {decision, reviewed, event_id}}."""
        stacks = {}
        undone = set()
        rows = self.db.execute(
            "SELECT * FROM events WHERE project=? ORDER BY id", (project,)).fetchall()
        for r in rows:
            if r["kind"] == "undo":
                undone.add(r["target_event_id"])
        for r in rows:
            if r["kind"] == "decision" and r["id"] not in undone:
                stacks[r["asset_id"]] = {"decision": r["decision"],
                                         "reviewed": bool(r["reviewed"]),
                                         "event_id": r["id"]}
        return stacks

    def state_of(self, project, asset_id):
        return self.asset_states(project).get(
            asset_id, {"decision": "undecided", "reviewed": False, "event_id": None})

    def record_decisions(self, project, items, group_key=None, presentation_id=None, note=None):
        """items: [(asset_id, decision)] ; always marks reviewed."""
        ids = []
        with self.tx():
            for aid, dec in items:
                if dec not in DECISIONS:
                    raise ValueError(f"bad decision {dec!r}")
                cur = self.db.execute(
                    "INSERT INTO events(ts,project,kind,asset_id,decision,reviewed,group_key,presentation_id,note,op_id)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (now(), project, "decision", aid, dec, 1, group_key, presentation_id, note,
                     ids[0] if ids else None))
                ids.append(cur.lastrowid)
            if ids:
                self.db.execute("UPDATE events SET op_id=? WHERE id=?", (ids[0], ids[0]))
        return ids

    def undo_last(self, project, count=1):
        """Corrective events targeting the most recent effective decision events."""
        undone_ids = []
        with self.tx():
            for _ in range(count):
                rows = self.db.execute(
                    "SELECT * FROM events WHERE project=? ORDER BY id", (project,)).fetchall()
                undone = {r["target_event_id"] for r in rows if r["kind"] == "undo"}
                live = [r for r in rows if r["kind"] == "decision" and r["id"] not in undone]
                if not live:
                    break
                # undo one whole decide call (all events sharing the latest op_id)
                last = live[-1]
                batch = [r for r in live if r["op_id"] == last["op_id"]]
                for r in batch:
                    self.db.execute(
                        "INSERT INTO events(ts,project,kind,asset_id,target_event_id,group_key,note)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (now(), project, "undo", r["asset_id"], r["id"], r["group_key"], "undo"))
                    undone_ids.append(r["id"])
        return undone_ids

    def backup(self, dest):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        out = sqlite3.connect(tmp)
        with out:
            self.db.backup(out)
        out.close()
        os.replace(tmp, dest)
        return dest


class _Tx:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.execute("BEGIN IMMEDIATE")

    def __exit__(self, et, ev, tb):
        self.db.execute("ROLLBACK" if et else "COMMIT")


def sha256_file(path, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def members_version(asset_ids):
    return hashlib.sha1(json.dumps(sorted(asset_ids)).encode()).hexdigest()[:12]
