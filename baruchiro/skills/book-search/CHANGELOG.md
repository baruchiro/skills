# Changelog

## 0.2.0
- Added a dedicated e-vrit browser procedure for title/author discovery, exact book/volume identity, separate digital/audio/print formats and the literal `ספריה ציבורית דיגיטלית` marker.
- Require rendered main-book details, allow asynchronous details to finish loading, distinguish unknown from a missing marker, and keep library-specific account/quota information outside the public package.
- Keep the provider-independent name `book-search`; `rebooks_search.py` remains the Rebooks-only helper, not the skill name. No e-vrit scraper or lending API is claimed.
- Added documentation contract checks, updated provider coverage and installation instructions, and regenerated the package manifest.
- Bumped shared plugin/marketplace metadata to 0.11.0. No GitHub Release/tag is implied.

## 0.1.1
- Bounded author and price extraction to each search-result or main-product element, with regression coverage for unrelated footer/sidebar metadata.
- Stop immediately on non-transient HTTP errors, including 403/429; retain bounded retries for transient HTTP failures.
- Added a clearly fictional alias example, Windows `py -3` commands, and explicit UTF-8 reads in package checks.
- Kept the consent-gated improvement-PR procedure and provider coverage limits; the MIT license is unchanged.
- Expanded validation to 20 offline helper regressions and 3 package checks.
- Bumped the shared `baruchiro` plugin/marketplace metadata from 0.10.3 to 0.10.4. This remains a package revision, not a merge, GitHub Release or live installation claim.

## 0.1.0
- Historical initial candidate of the generic book-search procedure; superseded by 0.1.1.
- Removed personal wishlist paths, branch preferences, historical book inventory and learned personal aliases.
- Added external-data instructions, access/parser limits, MIT license and clean-extraction checks; 0.1.1 supplies a fictional alias entry.
- No network reliability fix or new store adapter; no live skill changes, installation, push, PR or release.
