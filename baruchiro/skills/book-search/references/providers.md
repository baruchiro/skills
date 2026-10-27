# Provider coverage

The skill's search/identity/availability procedure is provider-independent. **Support for the procedure is not a claim that a Python adapter exists or that a store has been live-tested.** Select stores with the user; do not silently query every store.

| Provider | Public entry point | Search method | Coverage and verification |
|---|---|---|---|
| סיפור חוזר / Rebooks | https://rebooks.org.il/ | Included `scripts/rebooks_search.py` for title and author; web tools for final main-product verification | Executable adapter with 20 offline regression tests; title and author live searches verified in initial 0.1.0 preparation. Results are not a current stock promise. |
| עברית / e-vrit | https://www.e-vrit.co.il/ | Agent web tools: site title search, author search/page, exact product page | Generic web procedure only; no adapter or live search validation shipped. Separate digital, audio and print editions. For library eligibility require the exact product's explicit library label; this does not establish a specific library's licensing or current lending availability. |
| סטימצקי / Steimatzky | https://www.steimatzky.co.il/ | Agent web tools: site title search, author search/page, exact product page | Generic web procedure only; no adapter or live search validation shipped. Record the displayed format/edition and explicit stock text; online stock is not branch stock. |
| צומת ספרים / Tzomet Sfarim | https://www.booknet.co.il/ | Agent web tools: site title search, author search/page, exact product page | Generic web procedure only; no adapter or live search validation shipped. Record edition and explicit stock text; a price or search snippet alone is not availability. |

The last three are named starting points for the generic workflow, **not tested store-specific integrations**. If a page is blocked, search is unavailable, identity metadata is missing or the site changes, report the coverage gap and follow the required improvement-contribution procedure in SKILL.md. Do not replace missing metadata with guesses or claim exhaustive store coverage.

Other user-selected stores can use the same generic procedure when their public pages and access rules permit it. They are not additional tested providers until evidence and regression checks are contributed. Do not invent search endpoints or change the Rebooks helper's host.
