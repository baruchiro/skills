"""Tests on synthetic images only (no real photos, no network)."""
import hashlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from photocull import analyze as an  # noqa: E402
from photocull import ingest as ing  # noqa: E402
from photocull import session as ss  # noqa: E402
from photocull.store import LockedError, Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def scene(seed, size=(256, 192)):
    r = random.Random(seed)
    im = Image.new("RGB", size, tuple(r.randrange(256) for _ in range(3)))
    d = ImageDraw.Draw(im)
    for _ in range(40):
        x0, y0 = r.randrange(size[0]), r.randrange(size[1])
        box = [x0, y0, x0 + r.randrange(10, 90), y0 + r.randrange(10, 90)]
        col = tuple(r.randrange(256) for _ in range(3))
        (d.ellipse if r.random() < .5 else d.rectangle)(box, fill=col)
    return im


def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
            h.update(str(p.stat().st_mtime_ns).encode())
    return h.hexdigest()


def make_download(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "sub").mkdir(exist_ok=True)
    A = scene(1)
    A.save(root / "A.jpg", quality=92)
    (root / "sub" / "A copy (1).jpg").write_bytes((root / "A.jpg").read_bytes())  # exact dup
    A.resize((205, 154)).save(root / "A_small.jpg", quality=80)               # similar
    A.point(lambda v: min(255, v + 12)).save(root / "A_bright.jpg", quality=92)  # similar
    scene(2).save(root / "B.jpg", quality=92)
    scene(3).filter(ImageFilter.GaussianBlur(7)).save(root / "C_blurry.jpg", quality=92)
    for s in range(10, 16):
        scene(s).save(root / f"S{s}.jpg", quality=92)
    # EXIF time + orientation 6 (portrait), and a mtime-only file
    ex = Image.Exif()
    ex[0x0112] = 6
    ex[0x0132] = "2020:01:01 00:00:00"
    sub = ex.get_ifd(0x8769)
    sub[0x9003] = "2024:05:01 12:30:00"
    ex[0x8769] = sub
    scene(20).save(root / "exif.jpg", exif=ex, quality=92)
    scene(21).save(root / "sidecar.png")
    (root / "sidecar.png.json").write_text(json.dumps({"photoTakenTime": {"timestamp": "1700000000"}}))
    (root / "corrupt.jpg").write_bytes(os.urandom(500))
    (root / "phone.heic").write_bytes(b"\x00\x00\x00\x18ftypheic" + os.urandom(300))
    (root / "clip.mp4").write_bytes(b"not an image")
    os.utime(root / "B.jpg", (1600000000, 1600000000))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dl = Path(self.tmp.name) / "downloads"
        self.state = Path(self.tmp.name) / "state"
        make_download(self.dl)

    def tearDown(self):
        self.tmp.cleanup()

    def run_all(self, st):
        c = ing.ingest(st, self.dl)
        an.analyze_assets(st)
        return c, an.build_groups(st)

    def cli(self, *args):
        r = subprocess.run([sys.executable, "-m", "photocull", "--state", str(self.state), *args],
                           cwd=ROOT, capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)


class TestIngest(Base):
    def test_ingest_counts_dedupe_and_source_untouched(self):
        before = tree_hash(self.dl)
        with Store(self.state) as st:
            c, _ = self.run_all(st)
            self.assertEqual(c["dup_occurrences"], 1)
            self.assertEqual(c["other_files"], 2)  # mp4 + 1 json
            self.assertEqual(c["errors"], 0)
            n = st.db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            self.assertEqual(n, 15)  # 16 images - 1 exact dup
            two = st.db.execute("SELECT COUNT(*) FROM occurrences GROUP BY asset_id HAVING COUNT(*)=2").fetchall()
            self.assertEqual(len(two), 1)
            st_ = {r[0]: r[1] for r in st.db.execute("SELECT status,COUNT(*) FROM assets GROUP BY status")}
            self.assertEqual(st_, {"ok": 13, "unreadable": 1, "unsupported": 1})
            # library copies are byte-identical to what was downloaded
            for r in st.db.execute("SELECT sha256,library_path FROM assets"):
                self.assertEqual(hashlib.sha256((st.dir / r[1]).read_bytes()).hexdigest(), r[0])
        self.assertEqual(before, tree_hash(self.dl), "source folder was modified")

    def test_reingest_is_idempotent_and_touch_does_not_duplicate(self):
        with Store(self.state) as st:
            ing.ingest(st, self.dl)
            os.utime(self.dl / "B.jpg", (1700000001, 1700000001))  # mtime changes, bytes same
            c = ing.ingest(st, self.dl)
            self.assertEqual(c["new_assets"], 0)
            self.assertEqual(c["unchanged"], 15)
            self.assertEqual(st.db.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 15)

    def test_time_priority_and_orientation(self):
        with Store(self.state) as st:
            ing.ingest(st, self.dl)
            row = lambda n: st.db.execute(
                "SELECT a.* FROM assets a JOIN occurrences o ON o.asset_id=a.id WHERE o.source_path LIKE ?",
                (f"%{n}",)).fetchone()
            e = row("exif.jpg")
            self.assertEqual((e["taken_at"], e["taken_src"]), ("2024-05-01T12:30:00", "exif"))
            self.assertEqual((e["width"], e["height"]), (192, 256))  # orientation 6 swaps
            s = row("sidecar.png")
            self.assertEqual(s["taken_src"], "sidecar")
            self.assertTrue(s["taken_at"].startswith("2023-11-14"))
            b = row("B.jpg")
            self.assertEqual(b["taken_src"], "mtime")
            self.assertTrue(b["taken_at"].startswith("2020-09-13"))

    def test_bad_file_does_not_stop_batch(self):
        import photocull.ingest as m
        orig = m.sha256_file
        def boom(p, *a, **k):
            if str(p).endswith("S12.jpg"):
                raise OSError("disk hiccup")
            return orig(p, *a, **k)
        m.sha256_file = boom
        try:
            with Store(self.state) as st:
                c = ing.ingest(st, self.dl)
                self.assertEqual(c["errors"], 1)
                self.assertEqual(st.db.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 14)
                self.assertEqual(st.db.execute("SELECT COUNT(*) FROM ingest_errors").fetchone()[0], 1)
        finally:
            m.sha256_file = orig
        with Store(self.state) as st:  # retry picks up the missing file
            c = ing.ingest(st, self.dl)
            self.assertEqual(c["new_assets"], 1)

    def test_refuses_nested_state_dir(self):
        with Store(self.dl / "state") as st:
            with self.assertRaises(SystemExit):
                ing.ingest(st, self.dl)

    def test_single_writer_lock(self):
        with Store(self.state):
            with self.assertRaises(LockedError):
                Store(self.state)


class TestAnalyze(Base):
    def test_groups(self):
        with Store(self.state) as st:
            _, g = self.run_all(st)
            name = lambda aid: Path(st.db.execute(
                "SELECT source_path FROM occurrences WHERE asset_id=? ORDER BY id LIMIT 1",
                (aid,)).fetchone()[0]).name
            groups = {r["key"]: (r["kind"], [name(i) for i in json.loads(r["members"])])
                      for r in st.db.execute("SELECT * FROM groups WHERE active=1")}
            sim = [m for k, m in groups.values() if k == "similar"]
            self.assertEqual(len(sim), 1)
            self.assertEqual(set(sim[0]), {"A.jpg", "A_small.jpg", "A_bright.jpg"})
            blurry = [m for k, m in groups.values() if k == "blurry"]
            self.assertEqual(blurry, [["C_blurry.jpg"]])
            seq = [n for k, m in groups.values() if k == "sequence" for n in m]
            self.assertEqual(len(seq), 13 - 3 - 1)  # ok assets minus similar and blurry
            # every ok asset is reviewable exactly once
            allm = [i for r in st.db.execute("SELECT members FROM groups WHERE active=1")
                    for i in json.loads(r[0])]
            self.assertEqual(len(allm), len(set(allm)))
            self.assertEqual(len(allm), 13)
            # sharpness: blurred is far below sharp
            sh = {name(r[0]): r[1] for r in st.db.execute("SELECT id,sharpness FROM assets WHERE status='ok'")}
            self.assertLess(sh["C_blurry.jpg"], an.DEFAULT_BLUR_THRESHOLD)
            self.assertGreater(sh["B.jpg"], 10 * sh["C_blurry.jpg"])

    def test_analysis_is_deterministic_and_incremental(self):
        with Store(self.state) as st:
            ing.ingest(st, self.dl)
            n1, _ = an.analyze_assets(st)
            first = [tuple(r) for r in st.db.execute("SELECT id,phash,sharpness FROM assets ORDER BY id")]
            n2, _ = an.analyze_assets(st)
            self.assertEqual((n1, n2), (13, 0))
            an.analyze_assets(st, force=True)
            self.assertEqual(first, [tuple(r) for r in st.db.execute("SELECT id,phash,sharpness FROM assets ORDER BY id")])

    def test_flat_image_gets_no_hash(self):
        self.assertIsNone(an.phash(__import__("numpy").full((64, 64), 128.0)))


class TestSession(Base):
    def prep(self):
        with Store(self.state) as st:
            self.run_all(st)

    def test_conversation_flow_resume_undo_export(self):
        self.prep()
        rc, s0 = self.cli("status")
        self.assertEqual(s0["decisions"]["unreviewed"], 13)
        rc, g1 = self.cli("next")
        self.assertEqual(g1["kind"], "similar")
        self.assertTrue(Path(g1["contact_sheet"]).is_file())
        self.assertEqual(sum(1 for i in g1["items"] if i["suggested"]), 1)
        # "process restart": new process, same group is offered again (resume)
        rc, g1b = self.cli("next")
        self.assertEqual(g1b["group"], g1["group"])
        rc, d = self.cli("decide", g1["group"], "--keep", "1", "--skip", "2", "--undecided", "3")
        self.assertEqual(rc, 0)
        rc, g2 = self.cli("next")
        self.assertNotEqual(g2["group"], g1["group"])
        # reviewed+undecided is a valid, durable state
        rc, s1 = self.cli("status")
        self.assertEqual(s1["decisions"], {"keep": 1, "skip": 1, "undecided_reviewed": 1, "unreviewed": 10})
        # undo is a corrective event: group returns to pending, history stays
        rc, u = self.cli("undo")
        self.assertEqual(len(u["undone_events"]), 3)
        rc, s2 = self.cli("status")
        self.assertEqual(s2["decisions"]["unreviewed"], 13)
        with Store(self.state) as st:
            kinds = [r[0] for r in st.db.execute("SELECT kind FROM events ORDER BY id")]
            self.assertEqual(kinds, ["decision"] * 3 + ["undo"] * 3)
        # redo, then export
        rc, g1 = self.cli("next", "--kind", "similar")
        self.cli("decide", g1["group"], "--keep", "1,3", "--skip", "2")
        out = Path(self.tmp.name) / "export"
        rc, e = self.cli("export", str(out))
        self.assertEqual(e["keep_count"], 2)
        man = json.loads((out / "manifest.json").read_text())
        keep_shas = {i["sha256"] for i in man["files"]}
        with Store(self.state) as st:
            expect = {st.db.execute("SELECT sha256 FROM assets WHERE id=?", (i["asset_id"],)).fetchone()[0]
                      for i in g1["items"] if i["pos"] in (1, 3)}
        self.assertEqual(keep_shas, expect)
        for f in man["files"]:
            self.assertEqual(hashlib.sha256((out / f["file"]).read_bytes()).hexdigest(), f["sha256"])
        # idempotent re-export
        rc, e2 = self.cli("export", str(out))
        self.assertEqual((e2["copied"], e2["already_present"]), (0, 2))
        # later undo -> stale export file is reported, never deleted
        self.cli("undo")
        rc, e3 = self.cli("export", str(out))
        self.assertEqual(e3["keep_count"], 0)
        self.assertEqual(len(e3["stale_files_not_deleted"]), 2)
        self.assertEqual(len(list(out.glob("*.jpg"))), 2)

    def test_decide_is_bound_to_presented_version(self):
        self.prep()
        rc, g = self.cli("next")
        # a new near-identical photo arrives after the group was shown
        extra = self.dl / "A_late.jpg"
        scene(1).resize((230, 172)).save(extra, quality=85)
        self.cli("ingest", str(self.dl))
        self.cli("analyze")
        rc, err = self.cli("decide", g["group"], "--rest", "keep")
        self.assertEqual(rc, 2)
        self.assertIn("changed", err["error"])
        rc, g2 = self.cli("next", "--kind", "similar")
        self.assertEqual(len(g2["items"]), 4)

    def test_decisions_survive_reingest_and_reanalysis(self):
        self.prep()
        rc, g = self.cli("next", "--kind", "blurry")
        self.cli("decide", g["group"], "--skip", "1")
        self.cli("ingest", str(self.dl))
        self.cli("analyze", "--force")
        rc, s = self.cli("status")
        self.assertEqual(s["decisions"]["skip"], 1)

    def test_rest_and_errors(self):
        self.prep()
        rc, g = self.cli("next", "--kind", "similar")
        rc, err = self.cli("decide", g["group"])
        self.assertEqual(rc, 2)
        rc, err = self.cli("decide", g["group"], "--keep", "9")
        self.assertEqual(rc, 2)
        rc, ok = self.cli("decide", g["group"], "--keep", "2", "--rest", "skip")
        self.assertEqual(ok["left_unreviewed_in_group"], [])

    def test_projects_are_independent(self):
        self.prep()
        rc, g = self.cli("next", "--kind", "blurry")
        self.cli("decide", g["group"], "--skip", "1")
        rc, s = self.cli("--project", "other", "status")
        self.assertEqual(s["decisions"]["skip"], 0)

    def test_export_refuses_source_folder(self):
        self.prep()
        rc, g = self.cli("next", "--kind", "blurry")
        self.cli("decide", g["group"], "--keep", "1")
        rc, err = self.cli("export", str(self.dl / "out"))
        self.assertEqual(rc, 2)

    def test_backup_roundtrip(self):
        self.prep()
        rc, b = self.cli("backup", str(Path(self.tmp.name) / "bk" / "index.sqlite3"))
        import sqlite3
        n = sqlite3.connect(b["backup"]).execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        self.assertEqual(n, 15)


if __name__ == "__main__":
    unittest.main()
