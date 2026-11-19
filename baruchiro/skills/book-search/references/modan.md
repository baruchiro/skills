# Modan search and product verification

This is a read-only browser procedure for https://www.modan.co.il/, not an executable adapter or a stock API. No account is needed for public search. Do not add to cart, purchase, reserve or sign in as part of a book lookup.

## Search

1. Open the homepage and use the search field labeled `חיפוש לפי שם ספר או סופר/ת`. Enter the full requested title and submit with Enter or the search button. Search the author separately in the same field. Preserve spelling variants as separate queries until identity is verified.
2. The observed search route is `/AllResultsfulltext?bskeyword=<URL-encoded query>`. Prefer the current site's visible search UI; use a saved route only after confirming that it still performs the intended search. Do not invent legacy search endpoints.
3. Check the rendered results heading, query and result count. Record each search URL and whether it returned results, an explicit empty result, an error or an incomplete page. A blank/loading page or failed request is not zero results. If site search fails, a site-scoped web search can supply candidates, not exhaustive coverage.
4. Follow result links to the main product page. Keep the resolved URL, omitting only verified tracking parameters, and deduplicate by that URL. Do not assume every product has a numeric ID or construct a product slug from its title. Follow any visible pagination or load-more controls, recording pages checked. If more results cannot be inspected, report incomplete coverage rather than guessing an endpoint or a total.

## Verify the main product

5. Match the main title and author, requested language, translation, edition and volume. Inspect `עוד על הספר` for publisher, publication year, binding and translation when present. A search hit or cover alone does not settle identity. Keep missing edition details unknown; do not infer a series number from a date.
6. Wait for the main product's price area to finish rendering. Record the current selling price separately from the crossed-out original price and any promotion label. The observed results card initially showed a list price while the rendered product showed a discounted price. A percentage badge alone is not a final price, and a product price is not a checkout total including delivery or fees. If no selling price settles, report price unknown.
7. Report availability separately from price. A `לרכישה` control or `הוספה לסל` label establishes a purchase option was displayed, not confirmed physical stock. Use explicit main-product availability text when present. If absent, say availability unknown and optionally note the displayed purchase option. Do not borrow stock or prices from recommendations, banners or unrelated cards. No branch-level stock, reservation or successful checkout is verified by this procedure.
8. Return the verified title/author/edition, resolved product URL, observation timestamp, displayed selling price/currency and availability evidence or unknowns. Avoid plot details and spoilers. Keep personal queries, wishlists and captured website content outside this package.

## Validation and limits

A small public-browser check on 2026-11-18 exercised one full-title query, its author's name in the same search field, and the matching main product's identity, edition details and rendered promotional price. An explicit empty-result query was also checked. These examples do not establish exhaustive indexing, spelling tolerance, pagination behavior, all editions, physical stock or checkout success. No Modan scraper or automated browser test is shipped. The offline documentation tests check this guide's required distinctions, not live site behavior.

Read [site limits](site-limits.md) and the site's current access rules before use. Stop on rate limiting or access denial; follow the host's browser/security rules for challenges. Keep checks small and sequential. Do not use this procedure for bulk crawling or unattended monitoring. If the page changes or required details cannot be verified, preserve completed evidence and report the specific coverage gap.
