# cr-clone-trainer multi-repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train one reviewer Clone per scope (`oss` / `work`) from all repos in that scope, with Claude-written comments excluded and no per-person content.

**Architecture:** The collector takes several `--repo` values and writes one merged, repo-tagged run; a small script lists a scope's repos and their local checkouts; the skill docs drive one training run per scope and publish only `SKILL.md`, `VOICE.md`, `MODEL.md` into the target plugin's `skills/` folder.

**Tech Stack:** Python 3 (stdlib), bash, `gh` CLI (REST search + GraphQL), `jq`.

**Spec:** `docs/superpowers/specs/2026-11-09-cr-clone-multi-repo-design.md`

## Global Constraints

- All paths below are under `baruchiro/skills/cr-clone-trainer/` unless absolute.
- Scopes: `oss` = repos outside `bewith-dev`, checkouts in `~/source/<repo>`, published to `~/source/skills/baruchiro/skills/`; `work` = `bewith-dev` repos, checkouts in `~/source/with/<repo>`, published to `~/source/with/cursor-rules/skills/`.
- Claude markers to exclude: the contents of `baruchiro/shared/agent-reply-marker.txt` (read at runtime, never hardcoded), plus the prefixes `<!-- ai-review-result:` and `<!-- ai-test-review-result:`.
- No WHO lens anywhere: not in lenses, calibration questions, `MODEL.md`, or examples.
- Raw data stays local in `~/.claude/cr-clone-runs/<clone-name>/`; never in a repo.
- Never clone a missing repo; list it and ask the user.
- No new test files (user rule). Verification is by running the scripts against real repos.
- Keep the existing rate-limit pauses in `run_gh`.
- Bump `baruchiro` plugin to `0.15.0` in `baruchiro/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Review Focus

- A repo slug passed in mixed case (`Eshaham/Israeli-Bank-Scrapers`) still matches conversation comments → covered by existing `casefold()` compare; verify in Task 1 step 4.
- A comment that quotes the marker inside a code block is still excluded → accepted (marker anywhere in body excludes); no test.
- A repo where the user has zero comments → collector writes an empty contribution, does not crash; Task 1 step 4 runs one such repo (`baruchiro/skills`).
- Same PR number in two repos must not collide → PR maps are keyed per repo; Task 1 step 4 checks `pr_url` repo matches `repo`.
- Missing checkout for a repo in scope → `scope-repos.sh` prints `MISSING`, trainer stops and asks; Task 2 step 2.

---

### Task 1: Collector — many repos, Claude comments excluded

**Files:**
- Modify: `scripts/collect-review-activity.py`

**Interfaces:**
- Produces: CLI `collect-review-activity.py --repo A/B [--repo C/D ...] --login L --output PATH`. Every interaction gains `"repo": "owner/name"`. `area_of` output becomes `"<repo-name>/<first two path segments>"`. Summary gains `counts.excluded_ai_comments: int` and `per_repo: [{repo, unique_prs, human_comments}]`. `clone_marked` is renamed `ai_marked` and is true for any Claude marker.

- [ ] **Step 1:** `--repo` becomes `action="append", required=True`. `collect()` loops repos: per repo it runs the existing search → reviews → conversation flow, building `normalized_prs` per repo, and tags each interaction with `repo`. Results from all repos are concatenated before batching, counting and candidate selection (candidates keyed by `(repo, pr_number)`). `repo_info`/`repo_created` are per repo.
- [ ] **Step 2:** Add `load_ai_markers() -> tuple[str, ...]` reading `Path(__file__).resolve().parents[3] / "shared" / "agent-reply-marker.txt"` (stripped) plus the two prefixes from Global Constraints; `is_ai_comment(body) -> bool` = any marker in body. Replace both `"<!-- clone-trace:" in body` checks with it; exclusion from `human_comments` and candidates already keys on this flag.
- [ ] **Step 3:** `python3 -m py_compile scripts/collect-review-activity.py` → no output.
- [ ] **Step 4: Verify on real repos**

Run (in background, scratchpad output):
`python3 -I scripts/collect-review-activity.py --repo eshaham/israeli-bank-scrapers --repo Baruchiro/Paperless-MCP --repo baruchiro/skills --login baruchiro --output $SCRATCH/t1/review-activity.json`

Expected: exit 0; then
`jq '[.inline_review_comments+.conversation_comments+.reviews | .[] | select(.ai_marked|not) | select(.body|test("<!-- (resolving-pr-review-comments:agent-reply|ai-review-result:|ai-test-review-result:)"))] | length' $SCRATCH/t1/review-activity.json` → `0` (no unflagged marked comment);
`jq '.per_repo' …summary.json` lists 3 repos, `baruchiro/skills` with `human_comments: 0`;
`jq '[.inline_review_comments[] | select((.pr_url|ascii_downcase|contains(.repo|ascii_downcase))|not)] | length'` → `0`;
`jq '.counts.excluded_ai_comments'` > `0`.

- [ ] **Step 5: Commit** `feat(cr-clone-trainer): collect several repos at once and skip Claude-written comments`

### Task 2: `scope-repos.sh` — list a scope's repos and checkouts

**Files:**
- Create: `scripts/scope-repos.sh`

**Interfaces:**
- Produces: `scope-repos.sh <oss|work> [login]` (login defaults to `gh api user --jq .login`). Prints TSV, sorted by count desc: `<prs_reviewed_or_commented>\t<owner/repo>\t<checkout path or MISSING>`. Exit 2 on a bad scope.

- [ ] **Step 1:** Implement: for `reviewed-by` and `commenter`, page GitHub search `is:pr <role>:<login> -author:<login>` plus `org:bewith-dev` (work) or `-org:bewith-dev` (oss), `per_page=100`, up to 10 pages, `sleep 3` before each call, stop on a short page; union PR URLs (dedupe), count per repo; checkout = `~/source/<name>` (oss) or `~/source/with/<name>` (work) when it is a git dir whose `origin` resolves to that `owner/repo` (case-insensitive), else `MISSING`.
- [ ] **Step 2: Verify** `bash scripts/scope-repos.sh work` → `bewith-dev/backend-services` first with a path; `bash scripts/scope-repos.sh oss` → includes `os-scar/overlay … MISSING`; `bash scripts/scope-repos.sh foo` → exit 2.
- [ ] **Step 3: Commit** `feat(cr-clone-trainer): list a scope's reviewed repos and local checkouts`

### Task 3: Skill docs — scopes, no WHO, local raw data, publish to plugin

**Files:**
- Modify: `SKILL.md`, `references/workflow.md`, `references/output-contract.md`, `references/automation-prompt-template.md`

**Interfaces:**
- Consumes: Task 1 CLI (repeated `--repo`, `repo` field, `ai_marked`, `per_repo`, `excluded_ai_comments`); Task 2 `scope-repos.sh` output.

- [ ] **Step 1: `workflow.md`.** Step 1 becomes "pick the scope" (ask `oss` or `work` with `AskUserQuestion`), run `scope-repos.sh`, show the table, propose dropping repos under 5 PRs, and stop to ask about every `MISSING` (clone or skip; never clone unasked). Step 2: run folder is `~/.claude/cr-clone-runs/<clone-name>/<UTC timestamp>/`; existing Clone is found in the scope's publish folder by `cr-clone-*` name. Step 3: one collector call with every chosen `--repo`; `git` ownership commands run with `git -C <that repo's checkout>`. Step 4: each comment's code check uses the checkout of its `repo`; `area_counts` are repo-prefixed. Remove WHO from the lens list and all examples; remove the Resync section. Note that `ai_marked` comments are already excluded and that remaining replies on own PRs may still include unmarked Claude text — weigh `as_author` replies lightly.
- [ ] **Step 2: `output-contract.md`.** Published layout: `<publish folder>/cr-clone-<name>/{SKILL.md,VOICE.md,MODEL.md}` only (no `repos/`, no `state.json`, no `runs/`). `MODEL.md` frontmatter drops `repository`, gains `scope: oss|work` and `repos: [...]`; attention map and reflexes are cross-repo themes grounded as `repo:path:line`; remove the WHO line from Default posture. Publish = write files on a branch in the target repo and show the diff; committing/PR is the user's call. Generated runtime `SKILL.md` step 1: load the Clone's one `MODEL.md` for any PR. Remove "suggest a resync".
- [ ] **Step 3: `SKILL.md` + automation template.** Lens list without WHO; one line on scopes and where each publishes; template line about "root training `state.json`" removed.
- [ ] **Step 4: Verify** `grep -rniE '\bWHO\b|resync|state\.json|~/\.agents|repos/github\.com' SKILL.md references` → no matches.
- [ ] **Step 5: Commit** `docs(cr-clone-trainer): train one Clone per scope across repos`

### Task 4: Release bookkeeping

**Files:**
- Modify: `baruchiro/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md` (cr-clone-trainer row: mention `oss`/`work` scopes)

- [ ] **Step 1:** Versions `0.14.0` → `0.15.0` in both manifests.
- [ ] **Step 2: Verify** `claude plugin validate baruchiro` and `claude plugin validate .` → `✔ Validation passed`; `bash baruchiro/shared/test-agent-reply-marker.sh` → exit 0.
- [ ] **Step 3: Commit** `chore(baruchiro): 0.15.0`
