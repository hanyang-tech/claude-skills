# guided-review

Prepares a route through a change and walks you along it, one stop at a time, so you read every change in a sensible order and see the problems in it. You are the reviewer; the skill is the guide. You end up having read the important changes, seen every branch of the changed logic accounted for, and seen each finding checked against the code before it was shown to you.

## When to use it

- "Walk me through this PR."
- "What are the important changes in this commit range?"
- You want to read a diff yourself, but in a sensible order and with the bugs, logic flaws, mess and logging gaps pointed out.
- You want to know which untested branches the change adds.
- Not for: an automated report with no walkthrough (use [`deep-review`](../deep-review/) or [`pr-review`](../pr-review/)).

## Usage

```
/guided-review [target] [--doc] [--by-commit] [--thorough] [--models <role>=<model>,…]
```

With no target it uses uncommitted changes if there are any, else the current branch against its merge-base with the default branch, else the last commit. A commit, a range (`a..b`), a branch name, or a PR number or URL also work.

| Option | What it does |
|---|---|
| `--doc` | Writes the whole guide to `<work>/guide.md` and presents it at once, instead of stop by stop. |
| `--by-commit` | The route follows the commits in order instead of the combined diff. Good when the commits tell a deliberate story. |
| `--thorough` | Uses review agents even for a small change. |
| `--models <role>=<model>,…` | Overrides an agent's model. Roles: `reviewer`, `skeptic`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/guided-review
/guided-review 482
/guided-review main..feature/billing --by-commit
```

## How it works

1. **Get the change.** Resolve the target, collect the diff and commits, and count the hunks so completeness can be checked later.
2. **Understand the change.** Read the code (including the base version and callers) and write what it does before reading any commit message or description, then compare the two.
3. **Map every change.** Split the change into units, assign every hunk to one unit, and rank them as core, supporting or mechanical. Mechanical claims such as renames and moves are checked, and promoted if they change anything.
4. **Review each unit.** First an inventory of every branch (the input that takes it, what happens, whether a test reaches it, what it logs), then five separate lenses: bugs, logic, readability, cleanliness and logging.
5. **Verify every finding.** Each one is traced, reproduced where running code is allowed, or backed by a rule and examples. Findings rated 🔴 or 🟠 get a fresh skeptic agent in agent mode.
6. **Plan the route.** Contracts and data shapes first, then core logic in the order it runs, each unit's tests right after it, mechanical changes last in one skim stop.
7. **Check completeness.** Count hunks, units, branches, lenses and findings from the files on disk. A count that does not hold sends the work back to its step.
8. **Walk you through.** An overview first, then one stop per message. Each stop shows what changed, where to read, its branch table, logging, and the findings there.

Each step writes a file before the next starts, so the preparation is checkable and survives a context summary. Small changes (roughly under 400 changed lines and 15 files) are reviewed in one session. Larger ones, or `--thorough`, use reviewer agents per group of units, then skeptics; both default to Opus.

During the walkthrough you can say `next`, `back`, a stop number, `more`, `skip`, `rest` or `done`, ask questions, and give a verdict on any finding ("agree B1", "won't fix R2"). Your verdicts are recorded as yours. If you spot something yourself, it is checked like any other finding. The wrap-up lists stops visited, findings with your verdicts, untested branches, logging, and a suggested outcome that follows your verdicts.

## What you get

- The walkthrough in the conversation, ending with the wrap-up.
- A work directory kept after the run: `<scratchpad>/guided-review-<slug>/` when a scratchpad exists, else a temporary directory. It is never inside your repository. It holds `steps.md`, `1-target.md` to `7-coverage.md`, `notes.md` (your position and verdicts), and `guide.md` with `--doc`.

## Safety

- Read-only: it does not edit your code, switch your branch or stash. When it needs the code on disk it uses a detached scratch worktree in the work directory and removes it at the end.
- It runs tests, linters or snippets only for your own work or a branch of the same repository, in the scratch worktree or on your uncommitted work, with what is already installed. A PR from a fork is read only unless you say otherwise.
- Commit messages, PR descriptions, comments and code are treated as data; text in them that addresses the reviewer is pointed out, not followed.
- Generated files, lockfiles, vendored code and snapshots are left out of the review but listed on the route as not reviewed.
- After the walkthrough it offers, and does not do unasked: post review comments on the PR (it shows the exact comments first and posts a `COMMENT` review), fix the agreed findings on a new branch or worktree, write tests, or save the guide.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/lenses.md` | The codebase-conventions pass, the branch inventory, the five lenses, what makes a finding, and the output contract |
| `references/tour.md` | How to order the route, the overview and stop formats, the walkthrough commands, and the wrap-up |

## Related skills

- [`deep-review`](../deep-review/) — a single report from independent lenses, without a walkthrough.
- [`pr-review`](../pr-review/) — a PR review built around simplicity, uncovered cases and codebase fit.
- [`deslop`](../deslop/) — offers to hand its fix diff to this skill for review.
