# סיפור חוזר / Rebooks

## Search entry point

```sh
python3 scripts/rebooks_search.py "BOOK_TITLE" --mode title
python3 scripts/rebooks_search.py "AUTHOR_NAME" --mode author --max-pages 3
```

Public entry: https://rebooks.org.il/ . Executable title/author adapter, Python standard library. The script accepts the common query, --mode, --max-pages and --output flags. The existing search_books Python API remains available; its older default cap is 30, while the common CLI defaults to 3 (maximum 10). A cap/network/parser failure is incomplete, exit 2, never absence. The legacy adapter raises on failure and cannot retain earlier pages in its exception; do not claim partial records were saved for this source. Preserve completed output from other queries.

## Identity and availability

Run full title and author searches. Deduplicate by product ID. Confirm the exact main product title, author, language and volume. An explicit-empty marker differs from an unrecognized response. Recommendation cards and footer authors are not main-product data. Inspect the main product element id=product-ID and its instock/outofstock class before claiming stock. A price alone is not stock; website stock is not branch stock or a reservation.

## Limits and validation

Read [site limits](site-limits.md). Non-transient 403/429 errors stop immediately. No checkout, reservation or access-control bypass. Twenty offline helper regressions cover parsing, identity, pagination and HTTP behavior; live title/author checks were exercised during initial preparation, not a current stock promise.
