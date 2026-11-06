# Repository conventions

## Documentation layout

- **`README.md` (root)** — the marketplace home page. Describes every plugin and skill in a few lines and links to each plugin's own README. Keep detail out of it.
- **`<plugin>/README.md`** — the home page of one plugin: what it is, install steps, requirements, companions and usage. Written for people. When a plugin contains a single skill, this one file covers the skill too.
- **`SKILL.md`** — the agent interface of a skill: instructions the agent follows. Do not put user-facing install guides or promotion there; link to the plugin README instead.
- **Plugins with several skills** — if a skill needs its own user documentation, put a `README.md` beside its `SKILL.md`; the plugin README links to it.

When adding or changing a plugin or skill, update its README and the root README link in the same PR.
