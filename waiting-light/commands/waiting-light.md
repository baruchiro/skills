---
description: Arm or disarm the Home Assistant "waiting for you" light for this session
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/waiting-light.sh:*)
argument-hint: "[on|off|status]"
---

!`"${CLAUDE_PLUGIN_ROOT}/scripts/waiting-light.sh" ${ARGUMENTS:-toggle}`

Report the line above to the user verbatim, or a one-sentence paraphrase of it.
Do not run any other command and do not elaborate.
