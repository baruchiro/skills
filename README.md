# skills

Personal Claude Code skills marketplace.

## Install

```
/plugin marketplace add baruchiro/skills
```

| Plugin | What it gives you |
|---|---|
| `baruchiro` | Baruch's personal skills and agents |
| `pr-review-loop` | Drain review threads on your own PRs and track each PR's status in `pr-status.json`; pair it with the [PR Review Loop VS Code extension](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) |
| `waiting-light` | Flips a Home Assistant `input_boolean` while a session is waiting on you, so a light can signal it. See [waiting-light/README.md](waiting-light/README.md) |

```
/plugin install baruchiro@skills
/plugin install pr-review-loop@skills
/plugin install waiting-light@skills
```

## Structure

```
.claude-plugin/marketplace.json   # marketplace catalog
baruchiro/
  .claude-plugin/plugin.json      # plugin manifest
  agents/                         # subagent definitions
  skills/                         # SKILL.md files live here
pr-review-loop/
  .claude-plugin/plugin.json
  skills/resolving-pr-review-comments/  # skill, scripts and tests
  shared/                         # copy of the agent-reply marker
waiting-light/
  .claude-plugin/plugin.json
  hooks/hooks.json                # Stop / Notification / UserPromptSubmit / SessionEnd
  commands/                       # /waiting-light
  scripts/                        # the state machine
```

## Contents — `baruchiro`

### Skills

| Skill | What it does |
|---|---|
| `pr-readiness-verdict` | Quick pass: fast SAFE/RISKY/BREAKING verdict on a PR or diff, including whether it's even ready to review (stalled vs. active) |
| `pr-walkthrough` | Deep pass: review a PR (or matching PRs across repos) interactively, chunk by chunk |
| `test-quality-rubric` | Judge whether an existing unit test earns its keep — Delete, Merge or Rewrite |
| `working-in-a-fork` | Fork workflow: `main` mirrors upstream, `release` is your production branch, every feature goes to both |

### Agents

| Agent | What it does |
|---|---|
| `code-review-publish` | Post a completed review's findings to a GitHub PR as inline comments |

## Contents — `pr-review-loop`

`baruchiro` no longer contains `resolving-pr-review-comments`; existing users should also run `/plugin install pr-review-loop@skills`.

| Skill | What it does |
|---|---|
| `resolving-pr-review-comments` | Drain unresolved review threads on your own PRs — fetch, reply, resolve, check CI. Writes `pr-status.md` / `pr-status.json`, which the [PR Review Loop VS Code extension](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) shows in a sidebar |

### Companion VS Code extension

Install [PR Review Loop](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) to see the next PR needing you, PRs in review order, and whose turn it is (you, Claude, CI or CodeRabbit) in a live sidebar.

The extension displays `pr-status.json`; the `resolving-pr-review-comments` skill handles review threads and its `pr-status.sh` script writes the status file. The extension does not perform code reviews.

Requirements: Claude Code with the `pr-review-loop` plugin, [GitHub CLI](https://cli.github.com/) authenticated with GitHub, [jq](https://jqlang.github.io/jq/), and VS Code 1.90 or newer. Install the plugin from your terminal:

```sh
claude plugin marketplace add baruchiro/skills && claude plugin install pr-review-loop@skills
```

Run the skill for your PRs to generate `pr-status.json` in the project folder, then open that folder (or its `.code-workspace`) in VS Code. The sidebar appears once the file exists. In a trusted workspace, the extension refreshes status on a timer and watches the file for changes. See the [extension README](https://github.com/baruchiro/pr-status-vscode#readme) for file discovery and settings.
