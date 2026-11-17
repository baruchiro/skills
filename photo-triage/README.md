# photocull

Local photo intake and conversational culling. Baruch downloads photos once from the Google Photos
UI into a folder; everything after that is local: no Google, no OAuth, no network.

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Pillow, numpy
python -m photocull --state ~/photo-cull-state ingest ~/Downloads/photos
python -m photocull analyze
python -m photocull next                          # one group + contact sheet image
python -m photocull decide GROUP --keep 1,3 --skip 2 --undecided 4
python -m photocull undo
python -m photocull status
python -m photocull export ~/photos-keep          # copies kept photos + manifest.json + upload-list.txt
python -m photocull backup ~/backup/index.sqlite3
```
(Debian without `python3-venv`: `python3 -m venv --without-pip .venv`, then bootstrap with get-pip.py.)

Options: `--project NAME` (decisions are per project), `PHOTOCULL_STATE` env var.
Tests: `.venv/bin/python -m unittest discover -s tests` (synthetic images only).
Chat skill: `skill/photo-triage/SKILL.md`. Design notes and defaults: `docs/DESIGN.md`.

## Safety
* Source folder is read-only for this tool: nothing is deleted, moved or rewritten (tested by
  hashing the whole tree before/after). State dir may not be inside the source dir or vice versa.
* New bytes are copied once to `state/library/` (content-addressed, copy verified by sha256);
  all later work and export use those copies.
* Analysis only suggests groups. Decisions come only from `decide`.

License: MIT (see LICENSE). Ideas (EXIF/time, pHash) are inspired by g13n/photo-cull (MIT,
Copyright 2026 Gopalarathnam Venkatesan); no code was copied. Its keeper-selection model,
auto-reject and filename-based identity were deliberately not adopted.
