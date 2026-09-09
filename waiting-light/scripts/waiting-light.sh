#!/usr/bin/env bash
#
# waiting-light — flip a Home Assistant input_boolean while a Claude Code
# session is genuinely blocked on the user.
#
# Invoked two ways:
#   * by the plugin's hooks (hook-* subcommands), reading the hook JSON on stdin
#   * by the /waiting-light command (on|off|toggle|status), keyed on
#     $CLAUDE_CODE_SESSION_ID
#
# Arming is per session, so only the long session you armed can light anything.
# Every path exits 0: a hook must never be able to wedge a session.

set -uo pipefail

STATE_DIR="${HOME}/.claude/waiting-light"
CONFIG_FILE="${WAITING_LIGHT_CONFIG:-${HOME}/.claude/waiting-light.env}"

# background_tasks types that mean "not your turn yet". Types come from the
# Stop payload and are already filtered to running/pending by Claude Code.
# Backgrounded shells deliberately do NOT block: a long build running in the
# background still means it is your turn.
BLOCKING_TYPES="${WAITING_LIGHT_BLOCKING_TYPES:-subagent,workflow,teammate,cloud session}"

STALE_MINUTES=1440 # forget a session's waiting flag after 24h

log_error() {
  mkdir -p "$STATE_DIR" 2>/dev/null || return 0
  printf '%s %s\n' "$(date -Is)" "$*" >>"$STATE_DIR/errors.log" 2>/dev/null || true
}

# Absent or incomplete config => the plugin does nothing at all. This is what
# makes it safe to install on a machine that cannot reach Home Assistant.
load_config() {
  [ -r "$CONFIG_FILE" ] || return 1
  set -a
  # shellcheck disable=SC1090
  . "$CONFIG_FILE" || return 1
  set +a
  [ -n "${HA_URL:-}" ] && [ -n "${HA_TOKEN:-}" ] && [ -n "${HA_ENTITY:-}" ]
}

sanitize_sid() {
  # Session ids are UUIDs; refuse anything that could escape STATE_DIR.
  printf '%s' "$1" | tr -cd 'A-Za-z0-9._-'
}

# Parse the hook payload on stdin. Emits "<session_id>\t<blocked:0|1>".
parse_hook_stdin() {
  local payload
  payload="$(cat)"
  [ -n "$payload" ] || return 1

  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | jq -r --arg blocking "$BLOCKING_TYPES" '
      ($blocking | split(",") | map(ascii_downcase)) as $b
      | [(.session_id // ""),
         (if [(.background_tasks // [])[] | (.type // "") | ascii_downcase]
              | any(. as $t | $b | index($t)) then 1 else 0 end)]
      | @tsv' 2>/dev/null && return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$payload" | BLOCKING_TYPES="$BLOCKING_TYPES" python3 -c '
import json, os, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
blocking = {t.strip().lower() for t in os.environ["BLOCKING_TYPES"].split(",") if t.strip()}
tasks = d.get("background_tasks") or []
blocked = any(str(t.get("type", "")).lower() in blocking for t in tasks)
print("%s\t%d" % (d.get("session_id", ""), 1 if blocked else 0))
' 2>/dev/null && return 0
  fi

  log_error "no jq or python3 available to parse the hook payload"
  return 1
}

set_flag()   { mkdir -p "$STATE_DIR" && : >"$STATE_DIR/$1.$2"; }
clear_flag() { rm -f "$STATE_DIR/$1.$2" 2>/dev/null || true; }
has_flag()   { [ -e "$STATE_DIR/$1.$2" ]; }

push_to_ha() {
  local want="$1" service
  [ "$want" = "on" ] && service="turn_on" || service="turn_off"
  local body http
  body="$(printf '{"entity_id":"%s"}' "$HA_ENTITY")"
  http="$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' \
    -X POST \
    -H "Authorization: Bearer ${HA_TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "$body" \
    "${HA_URL%/}/api/services/input_boolean/${service}" 2>>"$STATE_DIR/errors.log")"
  case "$http" in
    2*) return 0 ;;
    *) log_error "HA ${service} on ${HA_ENTITY} returned HTTP ${http:-none}"; return 1 ;;
  esac
}

# Recompute the aggregate across every armed session and push it only when it
# actually changed, so HA sees one call per real transition.
sync_ha() {
  load_config || return 0
  mkdir -p "$STATE_DIR" || return 0

  local want="off" waiting base
  shopt -s nullglob
  for waiting in "$STATE_DIR"/*.waiting; do
    base="${waiting%.waiting}"
    # A waiting flag with no armed sibling is debris from a disarm.
    if [ ! -e "${base}.armed" ]; then
      rm -f "$waiting"
      continue
    fi
    # Sessions killed without SessionEnd would otherwise pin the light on.
    if [ -n "$(find "$waiting" -mmin "+${STALE_MINUTES}" -print -quit 2>/dev/null)" ]; then
      rm -f "$waiting" "${base}.armed"
      continue
    fi
    want="on"
  done
  shopt -u nullglob

  local prev=""
  [ -r "$STATE_DIR/aggregate" ] && prev="$(cat "$STATE_DIR/aggregate" 2>/dev/null)"
  [ "$want" = "$prev" ] && return 0

  # Only record the new value if HA actually accepted it, so a failed call
  # retries on the next hook rather than silently desyncing.
  if push_to_ha "$want"; then
    printf '%s' "$want" >"$STATE_DIR/aggregate"
  fi
}

# Serialise sync across concurrent sessions.
sync_ha_locked() {
  mkdir -p "$STATE_DIR" 2>/dev/null || return 0
  if command -v flock >/dev/null 2>&1; then
    ( flock -w 5 9 || exit 0; sync_ha ) 9>"$STATE_DIR/.lock"
  else
    sync_ha
  fi
}

cmd_hook_stop() {
  local parsed sid blocked
  parsed="$(parse_hook_stdin)" || return 0
  sid="$(sanitize_sid "${parsed%%$'\t'*}")"
  blocked="${parsed##*$'\t'}"
  [ -n "$sid" ] || return 0
  has_flag "$sid" armed || return 0

  if [ "$blocked" = "1" ]; then
    clear_flag "$sid" waiting
  else
    set_flag "$sid" waiting
  fi
  sync_ha_locked
}

cmd_hook_notify() {
  # Wired behind the permission_prompt matcher: Stop does not fire while an
  # approve/deny dialog is up, so this is the only signal for that state.
  local parsed sid
  parsed="$(parse_hook_stdin)" || return 0
  sid="$(sanitize_sid "${parsed%%$'\t'*}")"
  [ -n "$sid" ] || return 0
  has_flag "$sid" armed || return 0
  set_flag "$sid" waiting
  sync_ha_locked
}

cmd_hook_prompt() {
  local parsed sid
  parsed="$(parse_hook_stdin)" || return 0
  sid="$(sanitize_sid "${parsed%%$'\t'*}")"
  [ -n "$sid" ] || return 0
  clear_flag "$sid" waiting
  sync_ha_locked
}

cmd_hook_session_end() {
  local parsed sid
  parsed="$(parse_hook_stdin)" || return 0
  sid="$(sanitize_sid "${parsed%%$'\t'*}")"
  [ -n "$sid" ] || return 0
  clear_flag "$sid" waiting
  clear_flag "$sid" armed
  sync_ha_locked
}

current_sid() { sanitize_sid "${CLAUDE_CODE_SESSION_ID:-}"; }

require_config_or_explain() {
  load_config && return 0
  echo "waiting-light: not configured — create ${CONFIG_FILE} (see waiting-light.env.example in the plugin) with HA_URL, HA_TOKEN and HA_ENTITY."
  return 1
}

cmd_on() {
  local sid; sid="$(current_sid)"
  [ -n "$sid" ] || { echo "waiting-light: no \$CLAUDE_CODE_SESSION_ID in this shell; cannot arm."; return 0; }
  require_config_or_explain || return 0
  set_flag "$sid" armed
  # Do not set waiting here: the session is active right now. The next Stop
  # (or permission prompt) decides.
  clear_flag "$sid" waiting
  sync_ha_locked
  echo "waiting-light: ON for this session — ${HA_ENTITY} will turn on when this session is waiting on you."
}

cmd_off() {
  local sid; sid="$(current_sid)"
  [ -n "$sid" ] || { echo "waiting-light: no \$CLAUDE_CODE_SESSION_ID in this shell; cannot disarm."; return 0; }
  clear_flag "$sid" waiting
  clear_flag "$sid" armed
  sync_ha_locked
  echo "waiting-light: OFF for this session."
}

cmd_toggle() {
  local sid; sid="$(current_sid)"
  if [ -n "$sid" ] && has_flag "$sid" armed; then cmd_off; else cmd_on; fi
}

cmd_status() {
  local sid armed waiting aggregate configured
  sid="$(current_sid)"
  has_flag "$sid" armed && armed=yes || armed=no
  has_flag "$sid" waiting && waiting=yes || waiting=no
  aggregate="$(cat "$STATE_DIR/aggregate" 2>/dev/null || echo unknown)"
  load_config && configured="yes (${HA_URL%/} -> ${HA_ENTITY})" || configured="no (${CONFIG_FILE} missing or incomplete)"
  echo "waiting-light: armed=${armed} waiting=${waiting} ha=${aggregate} configured=${configured} session=${sid:-<none>}"
}

case "${1:-status}" in
  hook-stop)        cmd_hook_stop ;;
  hook-notify)      cmd_hook_notify ;;
  hook-prompt)      cmd_hook_prompt ;;
  hook-session-end) cmd_hook_session_end ;;
  on)               cmd_on ;;
  off)              cmd_off ;;
  toggle)           cmd_toggle ;;
  status)           cmd_status ;;
  *)                echo "waiting-light: unknown command '${1}'. Use on|off|toggle|status." ;;
esac

exit 0
