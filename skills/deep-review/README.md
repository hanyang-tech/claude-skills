# deep-review

A careful review of a code change. It first works out what the change is meant to do, then attacks it from several independent angles and tries to disprove each suspected problem before reporting it. You end up with a short list of confirmed bugs and risks, each with a concrete failure scenario.

## When to use it

- "Do a deep review of this branch before I merge it."
- "Look over this PR carefully; I want bugs, not style nits."
- You are about to merge something that touches auth, payments, migrations, public APIs or data deletion.
- You have a ticket or requirements and want the change checked against them, not just against itself.
- Not for: a PR review that centres on "could this be simpler" and "does it match our patterns" (use [`pr-review`](../pr-review/)), or reading a change yourself with a guide (use [`guided-review`](../guided-review/)).

## Usage

```
/deep-review [target] [--thorough] [--spec <path>] [--no-ask] [-- <requirements>]
```

With no target it reviews uncommitted work (diff plus untracked files), or the current branch against its merge-base with the default branch if the tree is clean. A PR number or URL, a branch name, a commit or range (`a..b`), or a file or directory path also work.

| Option | What it does |
|---|---|
| `--thorough` | Always fans out to parallel agents, even for a small change, and runs every one of them on Opus. |
| `--spec <path>` | Treats a requirements, ticket or design file as the authoritative intent. |
| `-- <text>` | Everything after a bare `--` is your requirements in your own words. |
| `--no-ask` | Never pauses to ask you questions (for unattended or CI runs). The intent is then assumed, and the report says so. |

Examples:

```
/deep-review
/deep-review 123 -- refunds must be blocked after 30 days
/deep-review feature/ledger-split --spec docs/ledger-split.md --thorough
```

## How it works

1. **Scope the change.** Resolve the target, then collect the diff, commit messages, and any PR description or linked ticket.
2. **Reconstruct the intent.** Write an Intent Statement (goal, expected behavior change, what must stay the same, invariants, approach), each part tagged with its source. Ticket and doc references are followed. The evidence is graded Strong, Weak or None. When it is Weak or None, a referenced ticket cannot be opened, or the change is high-risk, it asks you a few multiple-choice questions, once, built from what it saw in the diff. Skipped with `--no-ask` or when nobody is there to answer.
3. **Build context.** Read whole functions, callers of everything changed, sibling code paths, tests, contracts and project conventions, not just the hunks.
4. **Review through independent lenses.** Intent and logic, edge cases, failure modes, state and concurrency, security, contracts and compatibility, performance, tests, omissions, maintainability.
5. **Verify every candidate finding.** Try to disprove each one by tracing the code, checking for upstream validation, and running existing tests or a throwaway script where that is safe.
6. **Assign severity.** Blocker, Major, Minor or Nit.
7. **Report.**

Small changes (roughly under 300 changed lines and 10 files) are reviewed in one session, one pass per lens. Larger or high-risk changes, or any `--thorough` run, fan out to four fresh-context agents, each covering a group of lenses and briefed without the main agent's suspicions so each angle stays independent. Every Blocker or Major finding from a fan-out then goes to a separate skeptic agent whose job is to refute it. Models are set explicitly: Opus for intent, failure-mode and skeptic work, Sonnet for the performance, tests and maintainability group, and for security and compatibility unless the change is high-risk. If the session is not on Opus it tells you once that the main steps would be more reliable there.

Each finding ends as Confirmed or Plausible. Ideas that cannot be turned into a failure scenario become questions for the author, not findings.

## What you get

- A report in the conversation: a verdict (ready to merge, merge after fixes, needs rework), the Intent Statement, findings ordered by severity with a failure scenario, evidence and suggested fix each, questions for the author, what was checked and found sound, and coverage and limits (mode and models used).
- No files are written to your repository, and no work directory is created.

## Safety

- Read-only: it never edits, commits or pushes unless you ask after the review.
- Safe checks only: it may run existing tests or a tiny throwaway script in the scratchpad, but nothing destructive, nothing against production, and it does not modify the working tree to do so.
- Posting findings as PR comments happens only on your explicit request, and it shows you the exact comments first.
- After the review it offers, but does not assume, fixing the findings or adding tests for the failure scenarios.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/lenses.md` | The ten review lenses, each with a guiding question and checklist |

## Related skills

- [`pr-review`](../pr-review/) — a PR review organised around simplicity, uncovered cases and codebase fit, with files kept for each step.
- [`guided-review`](../guided-review/) — walks you through a change stop by stop so you read it yourself.
- [`conventions`](../conventions/) — records how the codebase is written, which gives a review project standards to judge against.
