# Israel Digital / OverDrive / Libby

Public entry: https://telaviv.overdrive.com/ . This source script reads `window.OverDrive.titleCollection` from search HTML, not the broader mediaItems/recommendation store. Title mode uses the public search query; author mode uses the creator filter observed in Advanced Search. It parses the explicit result count and keeps language, format, author/narrator/translator, publisher, series, ISBN where supplied, and copy/hold counts separately.

Libby is the reading/listening app for the OverDrive library collection, not an e-vrit subscription. A participating library card is required: https://telaviv.overdrive.com/support/card . Do not infer the user's library from their location or the telaviv hostname.

Signed-out pages warn that more titles/copies may appear after sign-in. All results are `public_collection_only`, with personal entitlement unverified. A complete public query is not complete coverage of the user's account.

Copy states: `available` requires availableCopies > 0; `no_licensed_copies` is ownedCopies == 0; `hold` means copies are all lent and isHoldable is true; otherwise `unavailable`. A hold control can coexist with zero licensed copies. No wait-time estimate is invented from hold counts. Missing/inconsistent counts are parser errors, not unavailable books. A title/format in another language is an alternative, not Hebrew availability.

Observed robots.txt disallows URLs with page parameters. This source script intentionally returns the first page only. If the declared total exceeds returned records, it sets complete=false, retains candidates and states the pagination gap. Narrow the query; never bypass the restriction. Empty requires both the explicit no-match marker and an empty titleCollection. A missing collection, unknown count, bot page or malformed record is an error.



## Search entry point

```sh
python3 scripts/overdrive_search.py "BOOK_TITLE" --mode title --output /tmp/overdrive-title.json
python3 scripts/overdrive_search.py "AUTHOR_NAME" --mode author --max-pages 3
```

Python 3.10+ standard library; no credentials or browser navigation. Run both queries. Use an output path outside the package. On Windows replace python3 with py -3. Author mode returns book candidates, not an author directory. `query_exact_match` ignores punctuation/spacing but does not equate translations, subtitles or volumes, and is not an identity verdict.

## Output and safety

The JSON includes provider/query/mode, timestamp, source pages, products, count, declared total, complete and errors. Each product separates identity, formats/languages, public availability and unverified personal entitlement. Exit 0 means complete for that public query; exit 2 means partial or failed and must not be reported as zero/absence. Preserve output, report the gap and do not silently drop completed records.

The network layer checks robots.txt for each fixed host, allows a missing robots file (404), and stops on other robots errors. It enforces at least two seconds between host requests or the stated crawl delay, validates same-host redirects and fixed search paths, bounds response bytes and timeouts, and never retries 403/429/errors. No automatic bot bypass. No scheduled crawling. Terms permitting ongoing automation were not established; keep checks small and read-only.

Never click Borrow, Place a Hold, wishlist/history controls, play/download books, start trials or change subscriptions/accounts during discovery. Those are separate authorized actions. No credentials or secrets are accepted by this script.

## Validation

Public scripted title and author searches exercised on 2026-11-20. Offline synthetic regressions cover parsing, explicit-empty versus error, copy states, language/format boundaries, token pagination, deduplication, partial preservation, robots denial, fixed-host redirects and HTTP stop behavior. No personal entitlement, playback or loan test. Public controls/product metadata were separately inspected on 2026-11-19; scripted catalog results do not replace a main-product/account check for stronger claims.

A later split-entry-point title check on 2026-11-20 returned incomplete for missing/inconsistent copy metadata. No results or availability were claimed; no retry. The structural change preserves this fail-closed behavior.
