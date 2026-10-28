---
name: gift-card-shopping
description: "Use when checking vouchers accepted at a merchant."
version: 0.1.0
author: Baruch Odem (baruchiro), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [shopping, gift-cards, vouchers, reverse-lookup]
---

# Gift-card shopping

Research exact voucher eligibility and answer “I'm at merchant X — which of my vouchers or memberships apply?” The optional Python helper joins a user-owned wallet to a local catalog; it does not fetch merchant lists, synchronize balances or guarantee checkout acceptance.

## When to Use
- Check a named merchant against the user's vouchers, memberships and benefits.
- Research where an exact voucher product can be used, including channel and item restrictions.
- Do not use for purchases, redemption, account login, secrets storage or background scraping.

## Prerequisites
Python 3.10+ (standard library only) for local lookup. Linux exercised; other platforms untested. Web retrieval tools are needed for separate public-source research, not for the helper. No credentials or API keys are required.

Before reading a real wallet, obtain consent for the exact external files. Explain that holdings and output read by the agent may reach conversation history/model providers, even when balance amounts are hidden. Never request PINs, redemption codes, barcodes, card numbers, tokens or personal redemption URLs.

Keep config, wallet, catalog and optional evidence cache outside this skill and every Git checkout. Paths in config resolve relative to that config. The engine reads inputs only; it does not create or update them. Read [privacy](references/privacy.md) and [limits](references/limits.md) before real use.

## How to Run
Resolve `SKILL_DIR` to this package directory. Through `terminal`, run:

```text
python3 "SKILL_DIR/scripts/voucher_lookup.py" validate --config "PRIVATE_CONFIG"
python3 "SKILL_DIR/scripts/voucher_lookup.py" lookup --config "PRIVATE_CONFIG" --merchant "MERCHANT_NAME" --channel physical --format json
```

Replace placeholders with approved paths/context. `--merchant-id ID` replaces `--merchant NAME`. Optional context: `--channel physical|online|marketplace`, `--branch-id ID`, `--seller-id ID`, `--on YYYY-MM-DD`. Default output is Hebrew text; JSON is available. Only add `--show-balances` when explicitly requested in this conversation. Amounts are user-reported, not synchronized.

There is no Python module entry point: invoke the script, not `python -m merchant_voucher_lookup`.

## Procedure
1. Establish merchant and exact voucher product. Separate issuer, program, product and personal holding: BUYME ALL and another BUYME product are not interchangeable. Use configured aliases; ambiguous matches require user selection, not a guess. Completion: one merchant identified or ambiguity reported.
2. Establish relevant channel/branch/seller. Do not infer online or marketplace acceptance from physical-store participation, or assume physical from “I'm at X.” Missing scope can require clarification. Completion: supplied context retained without invented values.
3. If an approved external config exists, run validation then lookup using the commands above. Read status, outcomes, reasons, source URLs and check dates; exit zero alone proves no eligibility. No applicable rule means unknown, not rejection. Completion: every claimed candidate tied to its exact product and evidence.
4. For research, inspect the issuer's current official directory and retailer payment terms; search actual merchant results, not an empty page shell or search snippet. Separate membership discounts/cashback from voucher redemption. Check item restrictions, seller and channel independently. See [research rules](references/research-rules.md). Completion: sourced finding or explicitly unverified lead.
5. Preserve conflicting rules and uncertainty. Stale, conditional or unverified evidence does not justify certain acceptance. Check current branch stock separately if the question is about buying today; online availability is not branch stock. Completion: no unsupported same-day or checkout claim.
6. Report verdict first, briefly: exact merchant/channel, supported candidates, unresolved conditions/exclusions and material gaps, with sources and actual check dates. Say “reported balance” if amounts were requested; never total balances or promise benefit stacking. Synthetic output is a demo, not real acceptance evidence. Completion: user can distinguish verified evidence, uncertainty and demo data.
7. Catalog/wallet changes require separate permission for the exact file and change. Propose source-backed updates rather than silently editing dates or amounts. No account synchronization is implemented. Completion: private state remains unchanged unless explicitly authorized separately.

## Contribution Back
When research reveals a reproducible reusable gap, preserve a sanitized finding with exact product/channel, official URL, observation date and limits. Propose the smallest source-backed correction with a regression check. Contribute through the host's approval process to the `gift-card-shopping` directory in `baruchiro/skills`; loading this skill grants no push/PR permission. Never export private inventories, preferences or authorization transcripts. Kanban workers use their governing learning-handoff policy instead of editing live skills. Routine lookups with no new finding need no filler contribution.

## Pitfalls
- Merchant participation does not establish eligibility for every product, promotion or channel.
- Empty/unloaded directories prove neither acceptance nor exclusion; third-party references are leads.
- Exact normalized names/explicit aliases only; no fuzzy search, inheritance or real merchant catalog is shipped.
- The helper is an early candidate, not full conformance to the design. Input-validation/privacy gaps and the limited test coverage are explicit in [limits](references/limits.md). Do not feed it unreviewed private files or promise exhaustive validation.
- A positive reported balance is not a checked current balance. Local execution is not a privacy sandbox.

## Verification
Through `terminal`, from this skill directory:

```text
python3 tests/smoke_cli.py
python3 tests/test_voucher_lookup.py
```

The first is a focused validate/lookup smoke check using temporary synthetic inputs outside Git. The second contains 19 offline regression functions, not 20; no live acceptance or full security verification follows from either. Do not describe unexecuted tests as passed. See README for a synthetic demo and migration notes.
