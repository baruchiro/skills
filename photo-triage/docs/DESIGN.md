# Design and defaults

Replaces the Picker-based phases P1-P5 of the earlier plan (decision 10.11.2026: one-time manual
download through the Google Photos UI). Retained from the plan: durable index, keep/skip/undecided
plus separate `reviewed`, undo as a corrective event, resume from durable state, MIT attribution.

## Data model (SQLite, WAL, single writer via flock)
* `assets` - identity = sha256 of bytes; filename is only an alias (`occurrences.source_path`).
  Same bytes from another path/batch = another occurrence (provenance kept), not a new asset.
  Changed bytes at the same path = new asset (old asset and its decisions untouched).
* `batches`, `ingest_errors`, `file_cache` (path,size,mtime -> skip re-hash on rescan).
* `groups` (suggestions, rebuilt by `analyze`; key = kind + hash of member ids = "version").
* `presentations` - exactly what was shown (ordered members + version). `decide` maps positions
  through it and is refused if the group has changed since (approval bound to what was shown).
* `events` - append-only; `decision` and `undo` (targets earlier events; undo reverts one whole
  `decide` call). Current state = replay. Project-scoped; skip in one project is not global.
* `export_receipts`. Schema version in `meta`.

## Defaults (all overridable on `analyze`)
| setting | default | why |
|---|---|---|
| pHash Hamming distance | 6 of 64 | catches resize/recompress/small brightness change; synthetic test separates unrelated scenes (>20) |
| blur threshold | Laplacian variance < 50 (on <=512px gray) | sharp synthetic ~600, blurred ~<10; real photos need calibration on Baruch's folder |
| group cap | 12 | one contact sheet must stay readable; larger clusters are split by time |
| sequence size | 12 | assets in no suggestion group are still reviewable, chunked by capture time |
| time priority | EXIF DateTimeOriginal > Takeout-style `.json` sidecar > EXIF DateTime > file mtime | recorded in `taken_src` |
Similar clustering is single-link (chains can merge loosely related shots); the cap splits them.
Flat images get no pHash. Exact duplicates are collapsed at intake and shown as `copies` on an item.
Unreadable files and HEIC/RAW (no codec) are stored and counted but not reviewable - listed in `status`.

## Export
`export DIR` copies `keep` (reviewed) assets as `YYYYMMDD_HHMMSS_<sha8>.<ext>` + `manifest.json`
(sha256, original paths) + `upload-list.txt`. Idempotent. If a later undo removes a kept photo,
the old exported file is reported as stale and never deleted. Refuses a destination that overlaps a
source folder or the state dir. Google album: Baruch uploads that folder manually.

## Not done / limits
See MISSING.md.
