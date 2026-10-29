# skills

Personal Claude Code skills marketplace.

## Install

```
/plugin marketplace add baruchiro/skills
```

| Plugin | What it gives you |
|---|---|
| `baruchiro` | Baruch's personal skills and agents |
| `pr-review-loop` | Drain review threads on your own PRs and track each PR's status in `pr-status.json`; pair it with the [PR Status VS Code extension](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) |
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

### Agents

| Agent | What it does |
|---|---|
| `code-review-publish` | Post a completed review's findings to a GitHub PR as inline comments |

## Contents — `pr-review-loop`

`baruchiro` no longer contains `resolving-pr-review-comments`; existing users should also run `/plugin install pr-review-loop@skills`.

| Skill | What it does |
|---|---|
| `resolving-pr-review-comments` | Drain unresolved review threads on your own PRs — fetch, reply, resolve, check CI. Writes `pr-status.md` / `pr-status.json`, which the [PR Status VS Code extension](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) shows in a sidebar |
