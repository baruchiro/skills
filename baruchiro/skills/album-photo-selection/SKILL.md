---
name: album-photo-selection
description: "Use when guiding someone through choosing, grouping and sequencing photos for a printed album."
version: 0.1.0
author: Baruch Odem (baruchiro), Instinct
license: MIT
---
# Album photo selection

A process guide for choosing and arranging photos for a family or period album. The agent coordinates the process and records decisions. It does not need access to the photos, and the user decides what goes in.

## When to Use
- The user has a pile of candidate photos and wants to get from it to an album, repeatedly or once.
- The user asks how many photos per event, what to do with near-identical shots, or how to order and pace a book.
- Do not use for connecting to a photo library, uploading photos, ordering prints, or deleting anything.

## Boundaries
- Work from what the user describes or shares. Never ask for a photo-library connection, login or bulk transfer. If the user has no wish to share images, the user looks and the agent only asks questions and keeps the log.
- Image analysis (finding blurry frames, grouping near-duplicates) is an optional step. The user, a local tool or another agent can do it, and the user chooses which. Treat its output as a suggestion, never a verdict.
- Never recommend deleting originals. The archive stays whole; the album is a selection from it. Moving a photo out of the album shortlist is reversible; say so.
- The staged workflow below is a suggestion. Offer it, adapt it to the user's own stages, and do not apply any stage as a hard rule.

## How to Run
1. **Intent.** Ask the user for one sentence on what the album should help them remember. Keep it in the log.
2. **Collect and group.** Distinguish *moment* (near-identical versions of one action), *event* (several moments that belong together) and *chapter* (a theme or period). Same date does not mean same event. See [guidance](references/guidance.md).
3. **Compare versions of a moment.** Ask the user to pick a representative and keep the others as alternates. Offer the test "if this one is out, what disappears?"
4. **Build each event's story.** Add a photo only when the user can say what it adds: context, key moment, relationship, detail, closing. One photo can be enough for an event; a rich event can take several.
5. **Order and pace.** Chronological by default, with events grouped inside. Check coverage (who or what is missing only because it was photographed less) without forcing equal space.
6. **Try spreads, then revisit.** Layout can change a choice: crowding, a bad crop, a lost context shot, a fold. Reopen selection when it does.
7. **Fresh look.** Suggest a break and a read-through from the start, or a second pair of eyes the user trusts.

At every stage, ask the user one decision at a time and offer a recommendation with the reason. Keep the log described in [decision log](references/decision-log.md).

## What is supported and what is suggested
[guidance](references/guidance.md) marks each recommendation as *source-supported* (professional editors and album or book makers say it) or *suggested workflow* (this skill's synthesis). Say which one you are relying on if the user asks why. The evidence is professional practice, not controlled research; it does not establish an ideal photo count.

## References
- [guidance](references/guidance.md): principles, with support level
- [worked example](references/example-beach-day.md): a fictional day at the beach
- [decision log](references/decision-log.md): what to record so work survives between sessions
- [sources](references/sources.md): ten sources with what each does and does not support
