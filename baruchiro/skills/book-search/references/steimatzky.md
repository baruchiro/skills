# סטימצקי / Steimatzky

## Search entry point

```sh
python3 scripts/steimatzky_search.py "BOOK_TITLE" --mode title
python3 scripts/steimatzky_search.py "AUTHOR_NAME" --mode author --max-pages 3
```

Public entry: https://www.steimatzky.co.il/ . The common entry point returns status=manual_required, complete=false, no network calls and exit 2. Automated search is not implemented. Empty products here means no automated search was performed, not no matching books. This entry point is an explicit capability handoff, not a working search adapter.

## Manual discovery and verification

Use the site's visible title search, then author search/page, and open each candidate's exact product page. If site search is unavailable, use site-scoped web discovery as a lead, not stock evidence. Do not invent endpoints. Record each attempted title/author search and its limits. Verify the main book's full title, author, language, edition and volume; exclude recommendations. Deduplicate by source and canonical product ID/URL. Follow permitted visible pagination or mark coverage incomplete.

## Availability and limits

Record formats separately. Require explicit main-product availability text; a price, buy button or search snippet does not prove stock. Online stock is not branch stock. Missing or blocked evidence is unknown, not sold out or absent. Save source URL, observed marker and timestamp outside the package. Read [site limits](site-limits.md); no anti-bot bypass, purchase, reservation or account change. No tested store-specific adapter or live validation is shipped. Other open contributions are not silently imported or merged here.
