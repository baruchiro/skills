# shared

`agent-reply-marker.txt` is a copy of `baruchiro/shared/agent-reply-marker.txt`. Both plugins must agree on it character for character: `resolving-pr-review-comments` (here) reads it to recognise agent replies, and the `code-review-publish` agent (in `baruchiro`) appends it to every comment it posts.

`baruchiro/shared/test-agent-reply-marker.sh` checks that the two copies are identical and that every place that spells the marker out matches.
