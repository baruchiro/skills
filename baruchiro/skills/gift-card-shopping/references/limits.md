# Candidate limits

The local helper is an early implementation, not verified full conformance to the design. This revision fixes packaging/documentation and performs a focused smoke check; it does not certify every engine behavior.

## Supported scope
- Read-only, on-demand JSON lookup; explicit config path.
- Separate issuer/program/product/holding/merchant, many rules per product and distinct holdings.
- Normalized exact names and explicit aliases; channel/branch/seller scope, rule dates, source metadata.
- Hebrew text or JSON; user-reported balances hidden by default.
- No network fetching, account login, balance sync, scraper, scheduler, writer, GUI or economic optimization.
- 10 MiB input-file size limit; Python standard library only. Linux exercised, other OS untested.

## Known implementation gaps (not accepted specification changes)
- Nested schemas are not fully closed; missing/wrong types can reach generic errors. Duplicate entity IDs can be overwritten during map construction; duplicate JSON keys and NaN are not explicitly rejected.
- Errors may echo paths/details. Config/package containment and overlapping inputs are not fully checked. Existing Git-boundary checks are not a security sandbox.
- Timestamp timezone/future-date validation and exact freshness thresholds are incomplete; freshness uses integer days. Fixtures with fixed dates age with the clock.
- Possible deny rules requiring missing context are not fully accounted for. Official-only validation, benefit-type conflict scope, and some unknown-balance behavior differ from the specification.
- Real/synthetic mixing is not rejected reliably; only supply reviewed all-synthetic inputs for this candidate's demo.
- The 19 original regression functions do not cover every required acceptance case: conflicts, deep schema/secret rejection, full path privacy and runtime network/write interception are not exhaustively tested. Source-import checks are not runtime socket-call interception.

Do not use these gaps to infer acceptance, guaranteed validation or safety with private data. A successful smoke check proves only the documented entry point and the assertions described in README. Full design acceptance and hardening remain unverified, not “all tests done.”
