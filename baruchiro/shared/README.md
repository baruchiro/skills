# shared

Values that more than one skill or agent in this plugin has to agree on
character for character.

| File | Who reads it |
|---|---|
| `agent-reply-marker.txt` | `resolving-pr-review-comments` (its fetch script reads it at runtime, its SKILL.md quotes it) and the `code-review-publish` agent (appends it to every comment it posts) |

A marker that drifts between producer and consumer fails silently — the
fetch script simply stops recognising agent replies and re-processes threads
that were already answered. `test-agent-reply-marker.sh` guards against that:
it asserts every place that spells the marker out matches this file.
