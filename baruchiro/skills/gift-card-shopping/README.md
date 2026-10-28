# Gift-card shopping — 0.1.0 candidate

Migration and extension of the gift-card shopping procedure, with a local reverse-lookup helper previously drafted as `merchant-voucher-lookup`. One skill directory covers both research and lookup; no second live skill is installed.

## Layout

Like the adjacent `book-search` skill, the entry file is `SKILL.md` with YAML name/description/version/author/license/platform metadata. Executable helpers live in `scripts/`, guidance in `references/`, synthetic examples in `examples/`, checks in `tests/`. No `merchant_voucher_lookup` Python module is shipped.

## Requirements and demo

Python 3.10+, standard library only. Linux exercised; no network/account access. From this package directory, through `terminal`, copy the **synthetic** examples to a new private, non-Git directory:

```sh
mkdir -m 700 "$HOME/voucher-demo"
cp examples/*.json "$HOME/voucher-demo/"
python3 scripts/voucher_lookup.py validate --config "$HOME/voucher-demo/config.json"
python3 scripts/voucher_lookup.py lookup --config "$HOME/voucher-demo/config.json" --merchant Kravitz --channel physical --format text
```

Do not overwrite an existing private directory. These examples use brand labels for test readability but all eligibility, amounts, dates and source excerpts are invented. Reserved `example.invalid` URLs cannot prove acceptance. As examples age the lookup can change to conditional: freshness uses runtime time even with `--on`.

A missing/unreadable config is an error, not “no vouchers.” Real use requires separately approved and manually reviewed external inputs. See [data model](references/data-model.md), [privacy](references/privacy.md), [research rules](references/research-rules.md) and [limits](references/limits.md).

## Checks

Through `terminal`, from this directory:

```sh
python3 tests/smoke_cli.py
python3 tests/test_voucher_lookup.py
```

`smoke_cli.py` runs only validation and a synthetic lookup and checks that the documented entry point works, output is marked synthetic, amounts are hidden, and five distinct fixture holdings are returned. It also counts the existing 19 regression functions using AST. It does not run that suite. `test_voucher_lookup.py` runs those 19 regression functions. Do not confuse inventory with passing results or claim full specification/security coverage.

## Migration and installation boundary

Use this directory as the single public candidate for extending `gift-card-shopping`; the helper's old internal identifiers are retained to avoid unnecessary engine changes. User-specific reminders, private research history and approval records from local installations are intentionally not exported. Existing private JSON stays outside Git and is not migrated automatically.

After owner approval and repository review, an interactive operator can install the complete skill directory using their agent's supported skill installation workflow. Do not install both this and the earlier standalone draft for the same purpose. This candidate performs no installation or live profile changes. Push, PR, merge and installation are separately authorized actions.

## License

Proposed MIT, consistent with the existing gift-card-shopping procedure and repository license; publication approval is pending. No external site content or real catalog is included.
