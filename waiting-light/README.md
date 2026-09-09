# waiting-light

Turns a Home Assistant `input_boolean` on while a Claude Code session is
genuinely waiting on **you** — and off the moment you answer. Point an HA
automation at that boolean and you get an ambient signal (a light changing
colour, say) for "the long session you left running needs you now".

Opt-in **per session**: only sessions you explicitly arm can light anything.

## Install

```
/plugin marketplace add baruchiro/skills
/plugin install waiting-light@skills
```

Then create `~/.claude/waiting-light.env` (see `waiting-light.env.example`):

```
HA_URL=http://homeassistant.local:8123
HA_TOKEN=<long-lived access token>
HA_ENTITY=input_boolean.claude_session_waiting
```

```
chmod 600 ~/.claude/waiting-light.env
```

**If that file is missing or incomplete, the plugin does nothing at all** — every
hook exits immediately. So it is safe to install on a machine that can't reach
Home Assistant.

Restart the session after installing so the hooks load.

## Use

| Command | Effect |
|---|---|
| `/waiting-light` | Toggle for this session |
| `/waiting-light on` | Arm this session |
| `/waiting-light off` | Disarm this session |
| `/waiting-light status` | Armed? waiting? what HA was last told? |

## What counts as "waiting for you"

| Signal | Meaning |
|---|---|
| `Stop` hook with no blocking background task | The turn ended and nothing is still running — your turn. |
| `Notification` hook, `permission_prompt` matcher | Blocked on an approve/deny dialog. `Stop` does **not** fire for this, so without it a session stuck on a permission ask would stay dark. |
| `UserPromptSubmit` | You answered — clear. |
| `SessionStart` | Session resumed (e.g. `claude --resume`) — clear, since you're back before typing anything. |
| `SessionEnd` | Clear and disarm, so the signal can't get stuck on. |

The `Stop` payload carries `background_tasks[]`, already filtered by Claude Code
to `running`/`pending`. A task whose `type` is `subagent`, `workflow`, `teammate`
or `cloud session` means it is *not* your turn yet, so the signal is suppressed.
Backgrounded **shells** deliberately do not suppress it — a long build running in
the background still means Claude is waiting on you. Override the list with
`WAITING_LIGHT_BLOCKING_TYPES` (comma-separated) in the env file.

Subagents themselves never trigger this: they fire `SubagentStop`, which this
plugin does not hook.

## How it behaves

- State lives in `~/.claude/waiting-light/` as `<session_id>.armed` /
  `<session_id>.waiting`. The boolean is on if **any** armed session is waiting,
  and HA is only written when its **actual** state differs from that. The
  entity's current state is read back before each write rather than trusting a
  local cache, so turning the boolean off by hand (a dashboard button, the HA
  app) cannot make the next real transition look like a no-op and swallow it.
  The `aggregate` file keeps the last pushed value purely as a fallback for when
  HA is unreachable, and as something `status` can show you.
- A failed HA call is logged to `~/.claude/waiting-light/errors.log` and does
  **not** advance `aggregate`, so the next hook retries and heals the state.
- A session killed without `SessionEnd` has its flags dropped after 24h rather
  than pinning the signal on forever.
- `curl --max-time 3`, and every path exits 0 — a hook must never wedge a session.

## The Home Assistant side

The plugin only flips the boolean; everything visual is yours. Create the helper:

**Settings → Devices & Services → Helpers → Toggle**, named so it lands on
`input_boolean.claude_session_waiting`.

Then an automation triggered by it. A minimal version:

```yaml
alias: Claude Code Session Waiting
triggers:
  - trigger: state
    entity_id: input_boolean.claude_session_waiting
    to: "on"
    id: waiting_on
  - trigger: state
    entity_id: input_boolean.claude_session_waiting
    to: "off"
    id: waiting_off
actions:
  - choose:
      - conditions: [{condition: trigger, id: waiting_on}]
        sequence:
          - action: scene.create
            data:
              scene_id: claude_waiting_restore
              snapshot_entities: [light.your_light]
          - action: light.turn_on
            target: {entity_id: light.your_light}
            data: {rgb_color: [128, 0, 255], brightness_pct: 40, transition: 2}
      - conditions: [{condition: trigger, id: waiting_off}]
        sequence:
          - action: scene.turn_on
            target: {entity_id: scene.claude_waiting_restore}
mode: queued
```

If the light is managed by **Adaptive Lighting**, take manual control before
tinting and release it after, otherwise AL will overwrite the colour on its next
interval:

```yaml
- action: adaptive_lighting.set_manual_control
  data:
    entity_id: switch.adaptive_lighting_all
    lights: [light.your_light]
    manual_control: true      # false in the waiting_off branch
```
