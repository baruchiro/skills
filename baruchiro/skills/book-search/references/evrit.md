# עברית / e-vrit: search, formats and public-library marker

This is a read-only procedure using the agent's `web_search`, `web_extract` and browser tools, not a Python adapter or a lending API. Use it when the requested store is עברית, including when checking whether a digital book carries the public-library marker. Search needs no account. Never purchase, redeem a code, reserve or email a library without separate authorization.

## Search and identify

1. Search the full requested title on https://www.e-vrit.co.il/ using the site's visible search UI. If unavailable, use `web_search` with `site:e-vrit.co.il/product/ "BOOK_TITLE"`. Replace BOOK_TITLE with the user's title; do not invent an internal endpoint. A snippet is a discovery lead, not availability evidence.
2. Search the author's name separately, using the site author page or `site:e-vrit.co.il "AUTHOR_NAME"`. Use title/author variants only as candidates until verified. Record which searches ran and which failed; no result from one spelling is not proof that the store lacks the book.
3. Open each plausible product URL in the browser. Confirm the MAIN book's title, author, requested language/translation and volume. For a series continuation, use the explicit numbered series information or linked series page rather than guessing from publication dates. Do not quote plot text or the sample chapter in the result; avoid spoilers.
4. Keep the canonical product URL and numeric `/product/<id>/` identity. URL slugs, Hebrew encoding and letter case can vary. Deduplicate by product ID, not search ranking or title alone. Do not confuse recommendation cards or other volumes with the main book.

Completion: exact main-product identity verified, with a URL; otherwise report uncertain/not found/error and the search limits.

## Check format separately from library eligibility

5. Inspect the main purchase/format area. Record digital (`דיגיטלי`), audio (`קולי`) and print (`מודפס`) independently; a print edition or price is not evidence of a digital edition. Do not click add-to-cart. A displayed digital option establishes a digital listing, not availability in a particular library account.
6. Wait for the rendered details to finish loading (the library marker can appear after the initial page load). Open or scroll to `עוד פרטים` and inspect the main book's details/tag region, before the reviews and recommendations. Look for the exact observed marker **`ספריה ציבורית דיגיטלית`**. It may be a link to e-vrit help rather than a borrow button. The digital format and this marker are **not equivalent**: verify and report both separately.
7. Capture the literal marker, its source product URL and the observation timestamp outside the package. Link wording can change; an unfamiliar variant is uncertain, not an automatically accepted alias. If the page is incomplete, blocked or the relevant details cannot be inspected, report eligibility as **unknown**, not false. If the fully inspected main details contain no marker, report “library marker not found on this page”, not “cannot be borrowed”. A library-related word in navigation, a help page, reviews or a recommendation is not evidence for the main book.

Completion: digital listing and library-marker observation each have their own evidence and result. Do not infer one from the other.

## Report and hand off

Use a short result with:
- Verified book title, author and volume when relevant.
- Direct canonical product URL.
- Digital listing: present / not shown / unknown.
- Library marker: exact observed label / not found in inspected details / unknown.
- Checked-at timestamp and any failed search or incomplete page.

An affirmative marker means the website marks this title for its public-library program. It does **not** establish a specific library's licensing, current code quota, user eligibility or a successful loan. If the user requests a loan, keep the library address, past correspondence, previous redemption date and waiting-period policy in separate user-owned records, never this public skill. Do not hardcode a library or a universal waiting period. Distinguish request date, code issue date and actual redemption/loan date; compute dates with tools, flag an unelapsed interval, and follow the user's approval boundaries before drafting/sending anything.

## Retrieval failures and verification

If `web_extract` cannot retrieve the page (including a search-only backend), use the real browser and inspect the rendered main details. Follow the host's shared-browser/tab rules. Stop for CAPTCHA, login/security gates or access denial; do not automate a bypass or retry a blocked endpoint. Do not turn a retrieval failure into “book unavailable”. Check current site restrictions before network use; this procedure does not grant permission for bulk crawling.

Live verification exercised title/author discovery and rendered main-product inspection on an e-vrit page on 2026-10-27: digital listing and the exact library marker were both visible. This is a point-in-time manual observation, not validation of every title or an executable adapter. The package's documentation checks verify discoverability and key distinctions only; they do not execute browser searches or prove future availability. When the layout changes, reproduce the gap and follow the skill's contribution rules.
