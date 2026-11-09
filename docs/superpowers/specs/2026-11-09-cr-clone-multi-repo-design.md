# cr-clone-trainer: one Clone per scope, trained across many repos

## Intent

The Clone must review PRs in open-source repos and at work. Today the trainer
builds one `MODEL.md` per checked-out repo, so every repo needs its own training
run and an untrained repo has no model. Instead, train one Clone per **scope**
from all the repos in that scope together.

## Scopes

| Scope | Repos | Local checkouts | Clone is published to |
|---|---|---|---|
| `oss` | every repo outside `bewith-dev` the user reviewed | `~/source/<repo>` | `baruchiro/skills` (public), `baruchiro` plugin |
| `work` | every `bewith-dev` repo the user reviewed | `~/source/with/<repo>` | `bewith-dev/cursor-rules` (internal), `bewith` plugin |

Each scope is its own Clone with its own `VOICE.md` (work and OSS comments may
differ in language and tone) and one `MODEL.md`.

## Goals

- One training run per scope covers all its repos.
- Comments are still checked against real code: the trainer opens the
  commented file in the local checkout and uses read-only `git` there.
- Comments Claude wrote under the user's account are excluded from learning.

## Non-goals

- Resync / incremental training.
- Training from issues.

## Anti-goals

- No per-person content. The **WHO** lens is removed: the Clone is published to
  shared repos, so nothing like "pushes harder on X's PRs" may be written.
- Raw data never lands in a repo. `runs/` (collected comments, drafts, `RUN.md`)
  stays local; only `SKILL.md`, `VOICE.md`, `MODEL.md` are published.

## Design

1. **Pick repos.** The trainer asks for the scope, then lists the user's
   reviewed/commented PRs per repo (GitHub search, `org:bewith-dev` or
   `-org:bewith-dev`) and shows counts.
2. **Resolve checkouts.** For each repo it looks in the scope's folder. Missing
   checkouts are listed and the trainer stops to ask; the user decides whether
   to clone or skip. Nothing is cloned without the user asking.
3. **Collect.** The collector runs per repo (unchanged: only the user's own
   comments, PRs only, rate-limit pauses) into one local run folder per scope.
   It drops comments whose body contains a Claude marker:
   `<!-- resolving-pr-review-comments:agent-reply -->` (read from
   `shared/agent-reply-marker.txt`), `<!-- ai-review-result:` and
   `<!-- ai-test-review-result:`. Unmarked Claude comments are accepted as noise.
4. **Learn.** As today, chunk by chunk, but each comment carries its repo; the
   code check runs in that repo's checkout.
5. **Model shape.** `MODEL.md` attention map and reflexes are written as
   themes that transfer across repos ("store mutations", "DB migrations"),
   each grounded with `repo:path:line` examples. Default posture and negative
   space stay. WHO is gone from the lenses, the questions and the output.
6. **Publish.** The Clone folder is written into the target repo's plugin
   (`cr-clone-<name>`), on a branch; committing/PR is the user's call.
   At review time the Clone reads its one `MODEL.md`, whatever the PR's repo.

## Approaches

- **Chosen: multi-repo training against local checkouts.** Keeps the real
  code + `git blame` check; checkouts mostly exist already.
- Rejected: fetch code from GitHub at the comment's commit. Works without
  checkouts but loses ownership (`blame`, authorship) signal.
- Rejected: train each repo, then merge. Many runs and calibration rounds for
  one result.

## Left to the builder

- Threshold for including a repo (a repo with 1–2 reviews adds little).
- Exact Clone name per scope (the trainer still asks).
- How the trainer finds the target plugin's `skills/` folder.
