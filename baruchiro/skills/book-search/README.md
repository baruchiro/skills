# Book search 0.1.0 — local publication candidate

Generic agent procedure for finding books in selected online stores; includes an unchanged, Rebooks-only Python helper. No claim of automated multi-store support. Not yet published or installed.

## Install (manual, only after reviewing the package)
Extract the full `book-search/` directory into a fresh, nonexisting directory. Review SKILL.md, scripts and LICENSE. Run the checks below before copying the complete directory into your agent's documented skill directory; do not overwrite an existing skill. In Hermes, resolve the active profile's skill location using its documentation rather than assuming a fixed home. Start a fresh session and verify `skill_view(name='book-search')` resolves that exact directory. This candidate was tested by clean extraction, not a live Hermes installation. Do not install into another profile implicitly.

## Use
Read SKILL.md. Supply titles/authors and desired stores explicitly. From this directory, via the agent's `terminal` tool:

```text
python3 scripts/rebooks_search.py "BOOK_TITLE" --mode title
python3 scripts/rebooks_search.py "AUTHOR_NAME" --mode author
python3 scripts/test_rebooks_search.py
```

Replace placeholders with real queries. Other stores: use public search/product pages through your web tools; no other scripted adapter is provided. No pip/npm installation, environment variables, API keys or user configuration is needed. Keep wishlists, query output, local aliases and settings outside this directory. `references/aliases.example.json` is empty on purpose; it is not loaded by the script. The agent reads a separate optional user-owned alias file.

## Checks and limitations
Python 3.10+ standard library. 16 offline regression tests cover duplicate IDs, stock, title/author matching, pagination, redirects/recommendations, Unicode URLs, foreign initial host rejection, block/empty/schema failures, normalization and page limits. Through `terminal`, run `python3 -B scripts/test_rebooks_search.py` and `python3 -m compileall -q scripts` in an extracted copy. The latter creates bytecode only in that copy; never ship it.

Linux tested; macOS/Windows not tested. Read references/site-limits.md before network use. A timestamped website observation is not a reservation, verified store-branch stock or current promise. Broad searches can time out; retain completed results and report gaps. A live check of another store was not performed.

## Source and license
Derived from the author's existing MIT-declared rebooks-search 0.1.0. The two Python files are preserved byte-for-byte; the generic workflow is documentation, not a code refactor. Credits: Baruch Odem (baruchiro), Hermes Agent. MIT license is included; site data/assets are excluded. The source install was a local copy, with no established canonical Git upstream. This package is the proposed new source snapshot, not an upstream update.

## Files
SKILL.md; README.md; LICENSE; CHANGELOG.md; scripts/rebooks_search.py; scripts/test_rebooks_search.py; references/site-limits.md; references/aliases.example.json; MANIFEST.json (SHA-256 of the other files). Evidence and private source mapping are separate attachments, never part of the public package.
