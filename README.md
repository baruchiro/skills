# skills

Personal Claude Code skills marketplace.

## Install

```
/plugin marketplace add baruchiro/skills
```

| Plugin | What it gives you |
|---|---|
| `personal` | Baruch's personal skills and agents |
| `waiting-light` | Flips a Home Assistant `input_boolean` while a session is waiting on you, so a light can signal it. See [waiting-light/README.md](waiting-light/README.md) |

```
/plugin install personal@skills
/plugin install waiting-light@skills
```

## Structure

```
.claude-plugin/marketplace.json   # marketplace catalog
personal/
  .claude-plugin/plugin.json      # plugin manifest
  skills/                         # SKILL.md files live here
  agents/                         # subagent definitions
waiting-light/
  .claude-plugin/plugin.json
  hooks/hooks.json                # Stop / Notification / UserPromptSubmit / SessionEnd
  commands/                       # /waiting-light
  scripts/                        # the state machine
```
