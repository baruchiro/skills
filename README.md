# skills

Personal Claude Code skills marketplace.

## Install

```
/plugin marketplace add baruchiro/skills
```

| Plugin | What it gives you |
|---|---|
| `baruchiro` | Baruch's personal skills and agents |
| `waiting-light` | Flips a Home Assistant `input_boolean` while a session is waiting on you, so a light can signal it. See [waiting-light/README.md](waiting-light/README.md) |

```
/plugin install baruchiro@skills
/plugin install waiting-light@skills
```

## Structure

```
.claude-plugin/marketplace.json   # marketplace catalog
baruchiro/
  .claude-plugin/plugin.json      # plugin manifest
  agents/                         # subagent definitions
  skills/                         # SKILL.md files live here
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
| `pr-walkthrough` | Review a PR (or matching PRs across repos) interactively, chunk by chunk |
| `resolving-pr-review-comments` | Drain unresolved review threads on your own PRs — fetch, reply, resolve, check CI |
| `test-quality-rubric` | Judge whether an existing unit test earns its keep — Delete, Merge or Rewrite |
| `pr-readiness-check` | Run first: is a PR stalled waiting on the author, or ready for a real review right now |
| `pr-safety-verdict` | Run once a PR is ready: fast SAFE/RISKY/BREAKING verdict — comments, backward compat, new-feature graceful degradation, and repo hygiene |

### Agents

| Agent | What it does |
|---|---|
| `code-review-publish` | Post a completed review's findings to a GitHub PR as inline comments |
