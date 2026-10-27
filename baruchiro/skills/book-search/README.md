# Book search 0.2.0

Find books across online stores, compare editions and verify website-reported availability. Supported starting points are Rebooks, e-vrit, Steimatzky and Tzomet Sfarim; the included Python helper automates Rebooks only. The [provider coverage table](references/providers.md) distinguishes tested automation from web procedures. For e-vrit, use the [dedicated search and library-marker procedure](references/evrit.md), exercised in the browser. The skill name is `book-search`, not `rebooks-search`; the provider-specific Python helper retains its Rebooks name because it only supports that site.

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

This installs the existing **baruchiro plugin bundle**, not a standalone book-search plugin. The shared plugin and marketplace metadata are aligned at version 0.11.0. Restart Claude Code and invoke `/baruchiro:book-search`. To test a reviewed checkout before publication, register that checkout instead, in a disposable Claude configuration:

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

Replace placeholders with real queries. Other stores use the agent's web tools and their own public search/product pages, not this helper. No API keys or environment variables are needed. Keep wishlists, output, settings and verified personal aliases outside the package. `references/aliases.example.json` is an optional external-data shape, not a file loaded by the script.

On Windows PowerShell, if `python3` is unavailable, use `py -3`:

```text
py -3 scripts/rebooks_search.py "BOOK_TITLE" --mode title
py -3 scripts/rebooks_search.py "AUTHOR_NAME" --mode author
py -3 scripts/test_rebooks_search.py
py -3 -m unittest discover -s tests -v
```

## Checks and limitations
Python 3.10+ standard library. The helper has 20 offline regression tests; package checks verify the complete file manifest/digests, the fictional alias example shape, relative documentation links, and the e-vrit procedure's discoverability and key distinctions. These documentation checks are not browser automation tests. They do not prove that an agent follows the contribution condition; that procedure is reviewed manually. In an extracted copy, run the commands above and `python3 -m compileall -q scripts tests` (Windows: `py -3 -m compileall -q scripts tests`); do not ship the resulting bytecode.

Linux tested; macOS/Windows not tested. Read [site limits](references/site-limits.md) before network use. A timestamped observation is not a reservation, branch-level stock or current promise. Broad searches can time out: preserve completed results and report gaps. Only Rebooks has a tested executable adapter. The e-vrit browser procedure was exercised on 2026-10-27 for product/author discovery, digital format and the public-library marker; no executable e-vrit adapter or live validation of the other stores is claimed.

## Source and license
Source and contribution target: [baruchiro/skills](https://github.com/baruchiro/skills), directory `baruchiro/skills/book-search`. PR: https://github.com/baruchiro/skills/pull/2. Derived from MIT-declared rebooks-search 0.1.0; the helper and tests include the fixes described in the changelog. Credits: Baruch Odem (baruchiro), Hermes Agent. MIT applies to this package, not provider data/assets. Package version is not a GitHub Release or evidence of installation.

## Files
SKILL.md, README.md, LICENSE, CHANGELOG.md, scripts/, tests/, references/ and MANIFEST.json (SHA-256 of every other package file). Private source mapping and execution evidence are not included.
