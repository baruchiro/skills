---
name: photo-triage
description: "Use when Baruch wants to cull a folder of downloaded photos in chat. Shows one group at a time, records keep/skip/undecided, resumes from durable state."
---

# photo-triage (conversational photo culling)

Local only: no Google login, no network, never touches the download folder. All state lives in
`$PHOTOCULL_STATE` (default `~/photo-cull-state`). The tool is `photocull` from the repo
(`<plugin-dir>/.venv/bin/python -m photocull ...`). Every command prints JSON.

## Flow
1. First time / new download: `ingest <download-dir>` then `analyze`. Report counts only
   (new, duplicate copies, unreadable, unsupported e.g. HEIC).
2. Each round: `next` (optionally `--kind similar|blurry|sequence`). Send the `contact_sheet`
   image and a short Hebrew caption: why the group (`why`), numbered items, the suggested
   keeper if any (`suggested`; say it is only a suggestion). Ask one question:
   "מה שומרים? (למשל: שמור 1,3 / דלג 2 / לא הוחלט 4)".
3. Map Baruch's answer to positions and run
   `decide <group> --keep 1,3 --skip 2 --undecided 4 [--rest keep|skip|undecided]`.
   Positions not mentioned stay unreviewed unless `--rest` is given. Confirm in one line
   and show the next group (`next` again).
4. "בטל" -> `undo` (undoes the last decide call as a corrective event).
5. "איפה עצרנו" / after any pause or new session -> `status`, then `next`
   (it re-offers the open group). Never rely on chat history for state.
6. "ייצא" -> `export <dir>` (never inside the download folder). Only `keep` is exported.
   Google album: tell Baruch to upload the exported folder himself; do not claim an album exists.

## Rules
- Suggestions (similar / blurry / keeper) are never decisions. Only Baruch's words create decisions.
- If `decide` returns "group changed", run `next` again and re-ask; do not reuse the old answer.
- "לא הוחלט" is a real answer (reviewed + undecided); do not nag about it.
- Never delete, move or edit source photos; no Google credentials; no sending photos to other services.
- Keep messages short, Hebrew, each line starting with a Hebrew word (RTL).

## Process (source of truth)
The approved end-to-end plan (monthly cull, then quota selection, stop points) lives in `docs/PROCESS.md` in this plugin (`photo-triage/docs/PROCESS.md`). Read it before starting a month; update it (bump version + changelog) when Baruch changes the method.
