# album-photo-selection

A skill that guides an agent through choosing, grouping and sequencing photos for a printed album, one decision at a time, while the user stays in charge. It was written for a recurring family-album workflow, and it does not need access to the photos.

- What it does: staged questions (intent, moments, events, story, order, spreads, fresh look), a decision log, and a clear split between source-supported advice and suggested workflow.
- What it does not do: connect to a photo library, analyse images itself, order prints or delete anything. Image analysis can come from the user, a local tool or another agent, and its output is a suggestion.
- Evidence: ten professional and vendor sources, listed in [references/sources.md](references/sources.md). They are practice, not controlled research, and give no ideal photo count.

Install with the `baruchiro` plugin, see the [root README](../../../README.md). The agent instructions are in [SKILL.md](SKILL.md).
