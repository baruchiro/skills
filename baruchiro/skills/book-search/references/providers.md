# Sources and targets

The machine-readable [sources.json](../sources.json) is the central source registry. Each target has exactly one source reference and one same-named search entry point. Shared modules beginning with an underscore are internal implementation code, not extra targets. Select sources with the user; do not silently search all sources.

| Target | Source reference | Search entry point | Capability |
|---|---|---|---|
| rebooks | [סיפור חוזר / Rebooks](rebooks.md) | [rebooks_search.py](../scripts/rebooks_search.py) | scripted_search |
| evrit | [עברית / e-vrit](evrit.md) | [evrit_search.py](../scripts/evrit_search.py) | manual_required |
| steimatzky | [סטימצקי / Steimatzky](steimatzky.md) | [steimatzky_search.py](../scripts/steimatzky_search.py) | manual_required |
| tzomet | [צומת ספרים / Tzomet Sfarim](tzomet.md) | [tzomet_search.py](../scripts/tzomet_search.py) | manual_required |
| overdrive | [Israel Digital / OverDrive / Libby](overdrive.md) | [overdrive_search.py](../scripts/overdrive_search.py) | scripted_search |
| storytel | [Storytel Israel](storytel.md) | [storytel_search.py](../scripts/storytel_search.py) | scripted_search |

Every entry point accepts QUERY, --mode title/author, --max-pages 1-10 (default 3) and --output PATH outside the package. Every common result includes provider, query, mode, checked_at, capability, reference, entry_url, status, complete, products, count and errors. Provider-specific identity/availability fields remain distinct. Exit 0 means complete for the stated public query only; exit 2 means incomplete/error/manual_required, never absence. Manual-required entry points do not perform a search.

Rebooks and the two public catalogs have real search implementations. e-vrit, Steimatzky and Tzomet still require the manual reference procedure; a uniform file layout does not imply equal automation. Existing e-vrit verification is partial, not a complete search or library adapter. This change does not incorporate other open provider PRs.
