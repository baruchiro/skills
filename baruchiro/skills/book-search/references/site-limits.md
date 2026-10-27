# Site access and helper limits

Check each store's current robots.txt, terms and access restrictions before use. Robots permissions are not a legal license or permission to crawl without limits. Use sequential small searches, avoid bulk crawling, stop on access denial/CAPTCHA/rate limiting, and wait for any stated Retry-After before another permitted request. Never use login cookies or buy/reserve without separate permission.

Rebooks uses a theme-specific HTML parser, not a supported public API. No affiliation is claimed. The observed robots.txt on 2026-10-27 did not disallow the public product search path; it disallows admin, logs and add-to-cart paths. Terms permitting automation were not established. Keep access read-only and small; seek site permission for ongoing/high-volume work.

The helper retries network failures and transient HTTP 408/425/5xx responses up to three times (30-second timeout per attempt; 1/2-second retry sleeps). Other HTTP errors, including 403 and 429, are propagated immediately. It does not implement Retry-After or delay between successful pages, and can run a long time with max_pages=30. Do not use it for unattended crawling. If denied or rate-limited, stop externally rather than repeating runs.

The initial URL is hostname-checked, but urllib follows redirects without rechecking the final hostname. This is not an SSRF security boundary; use only trusted public Rebooks URLs, not arbitrary URL input. No cookies or credentials are sent by this helper.

Parser limits: Hebrew search heading expected; theme-specific title, author and price markup remains required. HTML-aware div matching bounds extracted metadata to the product card/main product, but malformed card markup raises an error. Only instock/outofstock markers are recognized. Unknown stock remains `unknown`; malformed/blocked pages usually raise ValueError. An explicit empty marker is required for empty results, but fixtures do not prove immunity to every soft-block page. Independently verify main product identity and stock; related recommendation cards must not supply availability.

A broad live title search timed out in preparation. Offline tests passing does not establish current live search reliability. macOS and Windows are intended by stdlib-only implementation but were not exercised. Website data, cover images, inventory and terms are not covered by the code's MIT license and are not bundled.
