---
name: working-in-a-fork
description: Use when working in a git repo that is a fork of someone else's project (an `upstream` remote exists, or the user wants to fork a repo to contribute or run their own version) — setting up the fork, starting a feature, shipping or merging a feature, opening a PR to the original project, or syncing with upstream.
---

# Working in a fork

## Model

Three branches, three roles. The user runs `release`, contributes via `main`.

| Branch | Role | Rule |
|---|---|---|
| `upstream/main` | the original project | never push to it |
| `origin/main` | mirror of `upstream/main` | never commit on it; only fast-forward from upstream |
| `origin/release` | the user's production branch (what they install/run) | receives every feature, plus `main` after each sync |

Every feature branch starts from `main`, is merged into `release`, **and** gets a PR to `upstream/main`. "Ship it" means both, not just the upstream PR.

Before any block below that switches branches, run `git status --short`. If the tree is dirty, ask what to do with the changes. Afterwards, switch back to the branch the user was on. Any `--ff-only` that fails means a branch diverged: stop and ask.

## One-time setup

```bash
gh repo fork --remote --remote-name origin   # forks on GitHub
```

If `origin` already points at the original project (repo was cloned before forking), `gh` creates the fork but leaves the remotes alone ("a git remote named 'origin' already exists"). Rewire by hand:

```bash
git remote rename origin upstream
git remote add origin git@github.com:<me>/<repo>.git
git fetch origin && git branch -u origin/main main
git branch release main && git push -u origin release
```

Leave the fork's default branch as `main`.

## Start a feature

Sync first (below), then:

```bash
git switch main && git switch -c feat/<name>
```

Uncommitted work sitting on `main` moves along with `git switch -c`. Never commit it on `main`.

## Ship a feature

```bash
git push -u origin feat/<name>
git switch release && git pull --ff-only
git merge --no-ff feat/<name> && git push origin release
gh pr create --repo <upstream-owner>/<repo> --base main --head <me>:feat/<name>
```

The upstream PR is visible to other people. Show the title and body and get approval before running `gh pr create`. The merge into `release` is the user's own fork, so "ship it" covers it.

Use the upstream repo's PR template and commit style, not the fork's.

## Sync with upstream

```bash
git fetch upstream
git switch main && git merge --ff-only upstream/main && git push origin main
git switch release && git merge main && git push origin release
```

- If `--ff-only` fails, someone committed on `main`. Don't merge or reset it on your own.
- When upstream has merged one of the user's PRs (often squashed), `release` already holds the same change. The merge is usually clean. On conflict, take upstream's version, since that's what landed.
- Open feature branches whose PR is still pending: rebase onto `main` only if asked. They're pushed, so a rebase needs `--force-with-lease`.

## Common mistakes

- Opening the upstream PR and forgetting to merge into `release`, or the other way round.
- Branching a feature from `release`. It would carry every other unmerged feature into the upstream PR.
- Syncing `main` and not carrying it into `release`.
- Pushing anything to `upstream`.
