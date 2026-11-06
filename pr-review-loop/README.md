# pr-review-loop

Drain review threads on your own PRs and track each PR's status in `pr-status.md` / `pr-status.json`.

| Skill | What it does |
|---|---|
| `resolving-pr-review-comments` | Fetch unresolved review threads on your own PRs, reply, resolve, check CI, and write the status files |

## Install

```sh
claude plugin marketplace add baruchiro/skills && claude plugin install pr-review-loop@skills
```

Requirements: Claude Code, [GitHub CLI](https://cli.github.com/) authenticated with GitHub (`gh auth status`), and [jq](https://jqlang.github.io/jq/).

If you installed `baruchiro` earlier, run the install command above as well: `baruchiro` no longer contains `resolving-pr-review-comments`.

## Companion VS Code extension

Install [PR Review Loop](https://marketplace.visualstudio.com/items?itemName=baruchiro.pr-review-loop) (VS Code 1.90 or newer) to see the next PR needing you, PRs in review order, and whose turn it is (you, Claude, CI or CodeRabbit) in a live sidebar.

The extension only displays `pr-status.json`. The `resolving-pr-review-comments` skill handles the review threads, and its `pr-status.sh` script writes the status file. The extension does not perform code reviews.

1. Run the skill for your PRs. It writes `pr-status.json` in the project folder.
2. Open that folder (or its `.code-workspace`) in VS Code. The sidebar appears once the file exists.
3. In a trusted workspace, the extension refreshes status on a timer and watches the file for changes. In an untrusted workspace it only displays an existing file.

See the [extension README](https://github.com/baruchiro/pr-status-vscode#readme) for file discovery and settings.
