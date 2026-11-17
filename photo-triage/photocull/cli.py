"""photocull CLI. All output is JSON on stdout so the chat skill can read it."""
import argparse
import json
import os
import sys

from . import analyze as an
from . import ingest as ing
from . import session as ss
from .store import LockedError, Store

DEFAULT_STATE = os.environ.get("PHOTOCULL_STATE", os.path.expanduser("~/photo-cull-state"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="photocull")
    ap.add_argument("--state", default=DEFAULT_STATE, help="durable state dir (index + library copies)")
    ap.add_argument("--project", default="default")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest"); p.add_argument("source")
    p = sub.add_parser("analyze")
    p.add_argument("--phash-distance", type=int, default=an.DEFAULT_PHASH_DISTANCE)
    p.add_argument("--blur-threshold", type=float, default=an.DEFAULT_BLUR_THRESHOLD)
    p.add_argument("--sequence-size", type=int, default=an.DEFAULT_SEQUENCE_SIZE)
    p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("next"); p.add_argument("--kind", choices=["similar", "blurry", "sequence"])
    p.add_argument("--group")
    p = sub.add_parser("decide"); p.add_argument("group")
    p.add_argument("--keep"); p.add_argument("--skip"); p.add_argument("--undecided")
    p.add_argument("--rest", choices=["keep", "skip", "undecided"]); p.add_argument("--note")
    p = sub.add_parser("undo"); p.add_argument("--count", type=int, default=1)
    p = sub.add_parser("export"); p.add_argument("dest")
    p = sub.add_parser("backup"); p.add_argument("dest")
    a = ap.parse_args(argv)
    try:
        with Store(a.state) as st:
            if a.cmd == "ingest":
                out = ing.ingest(st, a.source)
            elif a.cmd == "analyze":
                n, bad = an.analyze_assets(st, a.force)
                out = {"analyzed": n, "failed": bad,
                       "groups": an.build_groups(st, a.phash_distance, a.blur_threshold, a.sequence_size)}
            elif a.cmd == "status":
                out = ss.status(st, a.project)
            elif a.cmd == "next":
                out = ss.present(st, a.project, a.kind, a.group)
            elif a.cmd == "decide":
                out = ss.decide(st, a.project, a.group, a.keep, a.skip, a.undecided, a.rest, a.note)
            elif a.cmd == "undo":
                out = {"undone_events": st.undo_last(a.project, a.count)}
            elif a.cmd == "export":
                out = ss.export_keep(st, a.project, a.dest)
            elif a.cmd == "backup":
                out = {"backup": str(st.backup(a.dest))}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    except (ss.UserError, LockedError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
