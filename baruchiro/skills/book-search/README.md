# Book search 0.2.3

Find books across online stores and public catalogs, compare editions and verify website-reported availability. Begin with the [central sources/targets list](references/providers.md) or [sources.json](sources.json). Rebooks, e-vrit, Steimatzky, Tzomet Sfarim, Israel Digital / OverDrive / Libby and Storytel Israel all have the same layout: references/SOURCE.md and scripts/SOURCE_search.py. Each source reference links its command, capability, identity/availability checks and limits.

Rebooks, OverDrive and Storytel have real search adapters. e-vrit, Steimatzky and Tzomet entry points honestly return manual_required/incomplete with exit 2 and point to their own procedure. They are not falsely advertised as automated. The pre-existing partial e-vrit verifier is retained separately. Shared underscore-prefixed modules are internal, not a separate multi-target command.

## Before using: improvement requirement
Use of this skill is conditional on accepting its [improvement procedure](SKILL.md#required-improvement-contributions). If a provider changes its site or required metadata is missing, the agent must investigate, test a minimal fix and open an upstream PR. Installation alone is not consent to public writes. Confirm this condition and obtain the required repository/publication permission before use; if permission or access is unavailable, report the blocker rather than claiming compliance. Do not publish personal queries, wishlists, credentials or site content.

## Install with skills CLI
Review the skill and its contribution condition first. With Node.js/npm available:

```sh
npx skills add baruchiro/skills --skill book-search --agent claude-code
```

This installs the selected skill in the current project, not every skill or a global profile. Choose another supported agent with `--agent` if needed. The default branch contains `book-search`; the command follows its current contents, not an immutable release. Use `--list` to inspect discovery without installation. These commands use the skills CLI; the helper itself has no npm/pip dependencies.

## Install as a Claude Code marketplace plugin
Inside Claude Code:

```text
/plugin marketplace add baruchiro/skills
/plugin install baruchiro@skills
```

This installs the existing **baruchiro plugin bundle**, not a standalone book-search plugin. The shared plugin and marketplace metadata are aligned at version 0.14.1. Restart Claude Code and invoke `/baruchiro:book-search`. To test a reviewed checkout before publication, register that checkout instead, in a disposable Claude configuration:

```text
/plugin marketplace add /absolute/path/to/reviewed/skills-checkout
/plugin install baruchiro@skills
```

Replace the path with the repository root containing `.claude-plugin/marketplace.json`. Do not mix two different checkouts under the same marketplace name. Plugin manifests and paths were checked; a live Claude Code installation has not been exercised here.

## Manual installation
Extract the complete `book-search/` directory into a fresh directory, review SKILL.md, scripts and LICENSE, and run the checks below. Copy the whole directory into your agent's documented skill location without overwriting an existing skill. Resolve the selected profile explicitly and verify the loaded path in a fresh session; do not install into another profile implicitly.

## Use
Read SKILL.md and confirm its improvement condition. Supply titles/authors and desired stores. From this directory:

```text
python3 scripts/rebooks_search.py "BOOK_TITLE" --mode title
python3 scripts/rebooks_search.py "AUTHOR_NAME" --mode author
python3 scripts/test_rebooks_search.py
python3 -m unittest discover -s tests -v
```

Replace placeholders with real queries. Every source uses the same QUERY, --mode title/author, --max-pages and --output arguments. For example, use scripts/overdrive_search.py for OverDrive or scripts/storytel_search.py for Storytel. All emit the common JSON envelope documented in the central list, plus source-specific product metadata. Exit 0 means complete for the stated public query; exit 2 is incomplete/error/manual_required, never absence. Manual-required sources perform no network calls. Their source reference describes the manual title/author search and final main-product check.

No credentials are needed. Catalog scripts check robots, use sequential GETs and pause at least two seconds per host. Keep queries narrow and save completed results outside the package. Keep wishlists, settings and verified aliases outside the package too. references/aliases.example.json is an external-data example, not automatically loaded.

On Windows PowerShell, if `python3` is unavailable, use `py -3`:

```text
py -3 scripts/rebooks_search.py "BOOK_TITLE" --mode title
py -3 scripts/rebooks_search.py "AUTHOR_NAME" --mode author
py -3 scripts/test_rebooks_search.py
py -3 -m unittest discover -s tests -v
```

## Checks and limitations
Python 3.10+ standard library. The Rebooks helper has 20 offline regression tests; 35 package/source/catalog tests include common CLI, registry, manual-required handoffs, preserved verifier/API, and parsers, pagination, partial results and HTTP/robots safety; package checks verify the complete file manifest/digests, the fictional alias example shape, relative documentation links, and the e-vrit procedure's discoverability and key distinctions. These documentation checks are not browser automation tests. They do not prove that an agent follows the contribution condition; that procedure is reviewed manually. In an extracted copy, run the commands above and `python3 -m compileall -q scripts tests` (Windows: `py -3 -m compileall -q scripts tests`); do not ship the resulting bytecode.

Linux tested; macOS/Windows not tested. Read [site limits](references/site-limits.md) before network use. A timestamped observation is not a reservation, branch-level stock or current promise. Broad searches can time out: preserve completed results and report gaps. Rebooks and the two public catalogs have tested search scripts. The e-vrit browser procedure was exercised on 2026-10-27 for product/author discovery, digital format and the public-library marker; the legacy partial e-vrit verifier is retained, but no complete automated title/author search or library-marker adapter is claimed. The earlier combined catalog title/author implementation was exercised on 2026-11-20; fresh split-CLI title checks later that day returned explicit incomplete/error for missing OverDrive copy metadata and Storytel HTTP 500, so no new live-success claim is made. Offline regression behavior is preserved; OverDrive pagination respects robots limits, and no personal entitlement is established.

## Source and license
Source and contribution target: [baruchiro/skills](https://github.com/baruchiro/skills), directory `baruchiro/skills/book-search`. PR: https://github.com/baruchiro/skills/pull/2. Derived from MIT-declared rebooks-search 0.1.0; the helper and tests include the fixes described in the changelog. Credits: Baruch Odem (baruchiro), Hermes Agent. MIT applies to this package, not provider data/assets. Package version is not a GitHub Release or evidence of installation.

## Files
SKILL.md, README.md, LICENSE, CHANGELOG.md, scripts/, tests/, references/ and MANIFEST.json (SHA-256 of every other package file). Private source mapping and execution evidence are not included.
