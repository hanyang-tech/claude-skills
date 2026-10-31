# pr-review

Reviews a pull request by first working out what it does from the code itself, then asking three questions of it: which cases does it miss, could it be simpler, and does it fit the codebase. You end up with a report where every finding comes with a concrete input, a sketch of the simpler code, or the existing code that shows the convention.

## When to use it

- "Review PR 482."
- "Look over this PR before I approve it."
- "Could this change be simpler?"
- "What edge cases does this miss?"
- "Does this follow our patterns?"
- Not for: a bug hunt against a ticket or spec with a requirements interview (use [`deep-review`](../deep-review/)), or reading the change yourself with a guide (use [`guided-review`](../guided-review/)).

## Usage

```
/pr-review [PR number | URL | branch] [--spec <path>] [--patterns <path>] [--thorough] [--models <role>=<model>,…]
```

With no target it reviews the PR for the current branch; if there is none, the current branch against its merge-base with the default branch. A branch name uses its PR if it has one, else the same merge-base comparison.

| Option | What it does |
|---|---|
| `--spec <path>` | A spec, ticket or design file to compare the change against. |
| `--patterns <path>` | The project's patterns file, if it is not at `docs/patterns.md`. |
| `--thorough` | Uses review agents even for a small PR. |
| `--models <role>=<model>,…` | Overrides an agent's model. Roles: `case-hunter`, `simplifier`, `conventions`, `skeptic`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/pr-review
/pr-review 482
/pr-review https://github.com/acme/api/pull/482 --spec docs/refunds.md
/pr-review fix/retry-uploads --thorough --models skeptic=fable
```

## How it works

1. **Get the PR.** Collect the PR, its diff, CI status and existing review comments.
2. **Understand the change from the code.** Read the changed code, its base version, callers and tests, and write the behavior changes (before → after) before reading the description. Then compare with what the author says.
3. **Learn how this codebase does things.** Find written rules and tool config, and open existing examples of each kind of thing the PR adds.
4. **Which cases are not covered?** Write a case inventory from eight sources (structure, old code, inputs, state, callers, dependencies, time, combinations), then trace each case through the code.
5. **Could this be simpler?** Sketch the simplest implementation of the behavior before studying the PR's own, then look for ten kinds of simplification, each checked against the case inventory.
6. **Does it fit the codebase?** Compare the PR with the conventions found in step 3. A convention counts only if it is written down or the existing code shows it at least twice.
7. **Verify and reconcile.** Try to disprove every candidate, run the PR's tests against a proposed simplification where allowed, and merge findings that touch the same code.
8. **Check completeness.** Count what was done from the files on disk.
9. **Report.**

The point of the steps is that each one writes a file before the next starts, so the review cannot go straight from diff to opinions. A small PR (roughly under 300 changed lines and 10 files) is reviewed in one session. A larger one, or `--thorough`, launches three agents in parallel: a case hunter and a simplifier on Opus, and a conventions checker on Sonnet. Findings rated must fix or should fix, and large simplifications, then get a fresh Opus skeptic. The case hunter and simplifier are kept apart on purpose, since one pulls towards more code and the other towards less.

When there is no description or spec the review carries on from the code alone and says so; it does not interview you.

## What you get

- A report in the conversation: recommendation (approve, approve after changes, request changes), what the PR does, stated vs. actual, uncovered cases, simpler alternatives, departures from the codebase, test gaps, questions for the author, what was checked and found sound, coverage counts, and limits. Findings are rated 🔴 must fix, 🟠 should fix or 🟡 consider.
- A work directory kept after the review: `<scratchpad>/pr-review-<n>/` when a scratchpad exists, else a temporary directory. It is never inside your repository. It holds `steps.md` and `1-pr.md` to `8-coverage.md`.

## Safety

- Read-only: it does not edit your code, switch branches, stash, or use `gh pr checkout`. When it needs the PR's code on disk it uses a detached scratch worktree in the work directory and removes it at the end.
- It runs tests, linters or snippets only when the PR is yours or from a branch of the same repository, only in the scratch worktree, and never installs dependencies. A PR from a fork is read only unless you say to run it.
- The PR title, description, comments and code are treated as data; text in them that addresses the reviewer is reported, not followed.
- Nothing is posted to GitHub unless you ask. It shows the exact comments first and posts a `COMMENT` review; it approves or requests changes only if you say so.
- It offers, and does not do unasked: trying a simplification on a new branch or worktree with the tests run, writing tests for the uncovered cases, and writing an inferred convention into the patterns file.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/conventions.md` | How to learn the codebase's conventions and check the PR against them |
| `references/cases.md` | How to enumerate and trace cases to find the ones not covered |
| `references/simplification.md` | How to sketch a simpler implementation and what each suggestion must show |

## Related skills

- [`deep-review`](../deep-review/) — a bug-focused review through independent lenses, with an intent interview.
- [`guided-review`](../guided-review/) — a stop-by-stop walkthrough of a change.
- [`conventions`](../conventions/) — records a codebase's conventions and can promote confirmed ones to `docs/patterns.md`, the file this skill checks against.
- [`deslop`](../deslop/) — removes generated-code padding rather than reporting on it.
