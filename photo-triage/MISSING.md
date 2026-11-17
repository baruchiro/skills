# Missing / open items

Needed from Baruch (none blocks review):
1. A real download folder (a sample of a few hundred photos is enough) to calibrate the blur
   threshold and pHash distance, and to run the real-data run log. Not run yet.
2. Which formats the Google Photos UI download gives him (JPEG only? HEIC? videos?). HEIC/RAW are
   currently stored but not reviewable (needs `pillow-heif`; not installed). Videos are ignored.
3. Skill is delivered as `skill/photo-triage/SKILL.md` in the repo, NOT installed: Kanban workers
   may not edit skills. Baruch decides when to have the interactive assistant install it.


Known limits (documented, not hidden):
* Tests cover synthetic images only; no crash-kill or full-disk simulation beyond per-file failure injection.
* `analyze` pairwise pHash is O(n^2) (vectorised); fine to roughly 20-30k photos, not tuned beyond.
* Contact sheet shows thumbnails, not originals; blur is hard to judge on thumbnails.
* Plugin lives in the public baruchiro/skills marketplace: never commit photos, state dirs or personal data.
