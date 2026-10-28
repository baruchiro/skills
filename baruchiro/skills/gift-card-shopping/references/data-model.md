# Data Model — merchant-voucher-lookup (schema_version 1)

This is the intended design contract, not a claim that all constraints are implemented. Read [current candidate limits](limits.md) for validation and privacy gaps. Examples below are synthetic explanatory templates, not verified merchant evidence.

## Overview

Four core entity tables (`issuers`, `programs`, `products`, `merchants`), plus `sources` (evidence metadata) and `rules` (acceptance/exclusion logic). A private `wallet.json` holds `holdings` referencing `products`. All references are by `id` (string, regex `[a-z][a-z0-9_-]{0,63}`).

## Entity Definitions

### issuer
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `name` | string | yes | Display name (≤120 chars) |

**Semantics:** Issuer only, not an acceptance family. Two products from the same issuer (e.g., BUYME ALL vs BUYME SELECT) are distinct and do not inherit rules from each other.

### program
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `issuer_id` | string | yes | Ref to `issuers.id` |
| `name` | string | yes | Display name (≤120 chars) |

### product
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `program_id` | string | yes | Ref to `programs.id` |
| `name` | string | yes | Display name (≤120 chars) |
| `kind` | enum | yes | `stored_value` \| `membership` \| `benefit` |

**Semantics:** A *precise* product. Variants with different terms (e.g., different expiry rules, different merchant sets) are separate products. `kind` determines wallet semantics:
- `stored_value`: monetary balance, `balance` object allowed (may be null = unknown)
- `membership`: club membership, no monetary balance, `balance` must be null
- `benefit`: perk/discount/cashback without stored value, `balance` must be null

### merchant
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `name` | string | yes | Canonical display name (≤120 chars) |
| `aliases` | string[] | yes (may be empty) | Alternative names for matching (Hebrew/Latin variants, common misspellings). Original case preserved for display. |

**Semantics:** A merchant/brand, NOT an automatic corporate group. Each merchant is independent; no inheritance from parent company.

### source
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `url` | string | yes | Public HTTPS URL (no userinfo, query, fragment, localhost, IP literal, single-label host). Personal redemption URLs not allowed. |
| `publisher` | string | yes | Publisher name (≤120 chars) |
| `authority` | enum | yes | `issuer_official` \| `merchant_official` \| `secondary` |
| `checked_at` | string | yes | RFC3339 timestamp when content was human-verified (not file load time) |
| `evidence_excerpt` | string | yes | Short quote from source (≤1000 chars, no control chars) |

**Verification rules:**
- `verified` rule requires ≥1 `issuer_official` or `merchant_official` source with non-empty excerpt, human-checked content match
- `secondary` alone never suffices for `verified`
- `checked_at` future timestamps rejected
- URL structural validation only; engine does not fetch or verify liveness

### rule
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier |
| `product_id` | string | yes | Ref to `products.id` |
| `merchant_id` | string | yes | Ref to `merchants.id` |
| `effect` | enum | yes | `allow` \| `deny` |
| `benefit_type` | enum | yes | `redemption` \| `discount` \| `cashback` |
| `scope` | object | yes | See Scope below |
| `conditions` | string[] | yes (may be empty) | Free-text conditions not modeled structurally (category limits, stacking, minimum spend, registration required, etc.) |
| `verification` | enum | yes | `verified` \| `unverified` |
| `source_ids` | string[] | yes | Refs to `sources.id` (unique, non-empty if `verified`) |
| `valid_from` | string\|null | yes | YYYY-MM-DD or null (inclusive lower bound) |
| `valid_until` | string\|null | yes | YYYY-MM-DD or null (inclusive upper bound) |

#### scope
```json
{
  "channels": ["physical" | "online" | "marketplace"],  // non-empty subset
  "branch_ids": string[] | null,   // null = all branches per source
  "seller_ids": string[] | null    // null = all sellers per source
}
```
- `online` ≠ `marketplace`; merchant online store acceptance does not imply marketplace acceptance
- Unknown channel is NOT `all`; missing context → `needs_context`
- Branch/seller IDs must be documented in source; no geographic lookup or branch table in MVP

## Integrity Constraints

1. All cross-references (`issuer_id`, `program_id`, `product_id`, `merchant_id`, `source_ids`) must resolve
2. IDs unique within each entity table
3. `source_ids` unique within a rule; non-empty if `verification: verified`
4. No duplicate JSON keys in any object (parser must reject)
5. `valid_from` ≤ `valid_until` when both non-null (inclusive bounds)
6. `checked_at` ≤ runtime (no future check times)
7. `data_kind`: `real` \| `synthetic` — never mixed in same lookup
8. File size limit: 10 MiB per input file (resource guard)
9. Wallet: each `holding` unique `id`; multiple holdings may reference same `product_id`; NO merging by label or product
10. Wallet `holding.kind` must match `product.kind`
11. `balance` object (if present): `amount_minor` ≥ 0 integer, `currency` 3-letter uppercase ISO, `reported_at` RFC3339 not future, `kind: "user_reported"` only
12. `stored_value` may have `balance: null` (unknown); `membership`/`benefit` must have `balance: null`
13. No free-text `notes` field in wallet — names/labels short text only

## Merchant Resolution

Normalization for matching only (original preserved for display):
- Unicode NFKC
- Casefold
- Trim + collapse whitespace sequences
- NO punctuation/diacritic removal, NO transliteration — use explicit `aliases` instead

Resolution:
1. `--merchant-id ID` → direct, mutually exclusive with `--merchant`
2. `--merchant NAME` → normalize, exact match on `merchant.name` or any `alias`
3. Single match → proceed
4. Multiple matches → `merchant_ambiguous` (return candidate IDs + names, NO wallet data)
5. No match → `merchant_not_found` (no inference about acceptance)

## Rule Evaluation Per Holding

For each holding where `holding.product_id == rule.product_id` and `holding.merchant_id == rule.merchant_id`:

### Scope Match
| Context Provided | Rule Scope | Result |
|------------------|------------|--------|
| channel in rule.channels | matches | `matches` |
| channel not in rule.channels | — | `does_not_match` |
| channel missing, rule requires specific | — | `needs_context` |
| branch_id provided, in rule.branch_ids | matches | `matches` |
| branch_id provided, not in rule.branch_ids | — | `does_not_match` |
| branch_id missing, rule.branch_ids non-null | — | `needs_context` |
| (same for seller_id) | | |

### Evidence Freshness
- Source fresh if `runtime - checked_at ≤ stale_after_days * 24h` (equality = fresh)
- `stale_after_days` from config (default 30, range 1–365)
- `balance_stale_after_days` separate threshold for wallet `reported_at`
- Secondary source never refreshes official source
- Rule `verified` + fresh official source = supported & current
- Rule `verified` + stale official source = supported but stale (→ `evidence_stale` reason)
- Rule `unverified` = never sufficient for `supported_candidate` or `excluded`

### Validity Period
- Rule active on eval date if `valid_from ≤ eval_date ≤ valid_until` (null = unbounded)
- Holding active if `status: active` AND (`expires_on` null OR `expires_on ≥ eval_date`)
- Expired rule/holding → not applicable (not a conflict)

### Decision Order (per holding)
1. **unavailable**: holding inactive OR expired on eval date OR `stored_value` with `balance.amount_minor == 0` (attach "reported zero; may have changed")
2. **conflict**: `allow` AND `deny` both `matches` in same context & period, both `verified` with official source (even if one stale). No "newer wins."
3. **excluded**: `deny` `matches` + `verified` + fresh official source, NO overlapping `allow` with same verification/freshness. Exclusion applies ONLY to provided context.
4. **conditional**: applicable `allow` exists BUT any of: missing context, non-empty `conditions`, `unverified`/`stale` evidence, unknown expiry, `balance_unknown`/`balance_stale`
5. **supported_candidate**: `allow` `matches` + `verified` + fresh official source, no conflict/deny/conditions, holding valid, expiry known. Balance unknown allowed (adds `balance_unknown` reason).
6. **unknown**: no applicable `allow`/`deny`, or all evidence outside rule period/context. "No matching info" ≠ "not accepted". Stale/unverified `deny` alone → `unknown` with `negative_lead`.

### Special Cases
- Overlapping `allow` (general) + `deny` (specific branch) without explicit positive scope for the general allow → **conflict**, not automatic precedence
- Data author must model positive scopes correctly or leave conflict for review
- Multiple rules for same holding → single holding output with all relevant `rule_ids` and combined reason codes

## Output Structure (JSON)

```json
{
  "schema_version": 1,
  "status": "ok|merchant_ambiguous|merchant_not_found|invalid_input|io_error",
  "data_kind": "real|synthetic",
  "evaluated_on": "YYYY-MM-DD",
  "observed_at": "RFC3339",
  "merchant": {"id": "...", "name": "..."} | null,
  "context": {"channel": "...", "branch_id": "...", "seller_id": "...", "on": "YYYY-MM-DD"},
  "merchant_candidates": [{"id": "...", "name": "..."}],
  "holdings": [
    {
      "holding_id": "...",
      "label": "...",
      "product_id": "...",
      "product_name": "...",
      "kind": "stored_value|membership|benefit",
      "outcome": "supported_candidate|conditional|conflict|excluded|unavailable|unknown",
      "reason_codes": ["..."],
      "expires_on": "YYYY-MM-DD|null",
      "balance_state": "unknown|reported_zero|reported_positive|not_applicable",
      "balance_freshness": "fresh|stale|unknown|not_applicable",
      "rules": [
        {"rule_id": "...", "effect": "...", "benefit_type": "...", "scope": {...}, "conditions": [...], "verification": "...", "source_urls": [...], "source_authorities": [...], "source_checked_at": [...], "valid_from": "...", "valid_until": "...", "freshness": "fresh|stale|unknown", "scope_match": "matches|needs_context|does_not_match"}
      ],
      "balance": null | {"amount_minor": N, "currency": "ILS", "reported_at": "...", "kind": "user_reported"}
    }
  ],
  "warnings": ["..."]
}
```

- `balance` always null without `--show-balances`
- Arrays present even when empty
- `status: ok` with empty `holdings` = "no registered assets for this merchant" (not "no benefits at merchant")
- Stable sort: outcome order (supported_candidate, conditional, conflict, excluded, unavailable, unknown), then normalized label, then holding_id

## Human-Readable Output (Hebrew, `--format text`)

```
רשת: Kravitz | ערוץ: פיזי | תאריך הערכה: 2026-10-28

✅ מועמדים נתמכים (לפי מקור):
- BUYME ALL Gift Card (שובר דוגמה א׳) — מימוש פיזי. מקור: BUYME הרשמי, נבדק 2026-10-01. נדרשת בדיקת תנאים בקופה.

⚠ דורשים בירור:
- חברות מועדון דוגמה ב׳ — אין מידע מתאים לערוץ זה. סיבה: context_missing.

❌ לא רלוונטיים:
- שובר דוגמה ג׳ — פג תוקף ב-2025.

לפי קטלוג מקומי נכון ל-2026-10-28. לא התחייבות לקבלה בקופה. יש לאמת מול הרשת/המנפיק לפני תשלום.
```

Synthetic data always marked: "נתונים סינתטיים — לא ראיית קבלה אמיתית"