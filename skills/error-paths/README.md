# error-paths

Walks the failure modes of a feature, endpoint, command or job: what happens when each thing it depends on fails. For every gap it writes a test that fails on the current code, and, with your yes, a fix that makes it pass.

## When to use it

- "What happens if the payment API times out in `POST /orders`?"
- "Review the error handling of the nightly sync."
- You want the unhappy paths of a change checked: retries, duplicates, partial failure, crashes mid-operation.
- You suspect failures are swallowed, logged without context, or leak internals to users.
- Not for: a general review of a diff (use [`pr-review`](../pr-review/) or [`deep-review`](../deep-review/)), or cleaning up swallowed errors and log noise in code you aren't tracing (use [`deslop`](../deslop/) with `--families ERR,LOG`).

## Usage

```
/error-paths [target] [options]
```

The target is a feature, endpoint, command or job in words (`POST /orders`, "the nightly sync"), paths or globs, or a commit, range, branch or PR. With no target it takes the operations touched by the uncommitted changes, else by the current branch. For a diff the whole operation is in scope, and rows outside the changed lines are marked `pre-existing`.

| Option | What it does |
|---|---|
| `--report-only` | Stop after the plan and present the matrix and plan as a report. Nothing is edited. |
| `--auto` | Write the tests without waiting for plan approval. Fixes still need your yes, one by one. |
| `--failures <list>` | Only these failures, by catalog code, e.g. `--failures TIME,PART,DUP`. |
| `--models <role>=<model>,…` | Override an agent's model. Roles: `mapper`, `skeptic`, `fixer`. Values: `sonnet`, `opus`, `fable`. |

The catalog codes are TIME, CONN, 5XX, 4XX, SHAPE, PART, DUP, RACE, CRASH, ORDER, FS, HOSTILE, EDGE, CLOCK, EXHAUST, SLOW, CANCEL and WRONG.

Examples:

```
/error-paths POST /orders
/error-paths the nightly sync --report-only
/error-paths src/jobs/ --failures TIME,PART,DUP
```

## How it works

1. **Get the target.** Scope, where changes go, whether code may be run.
2. **Map the operations and the codebase.** Entry points, written rules (`docs/conventions.md`, `docs/patterns.md`, API contracts), how the codebase already handles failure, test tools, and a baseline test run.
3. **Trace and inventory the failure points.** Follow each operation's call graph to every external interaction, with the failures that can and can't happen at each.
4. **Build the matrix.** One row per failure point and failure: current behavior traced with `path:line`, expected behavior with its source (or `unknown`), a verdict (`handled`, `gap`, `unknown`) and an impact.
5. **Verify every gap and unknown.** Try to disprove each: is it reachable, is it handled upstream. Skeptic agents take the data-loss, inconsistent-state and security gaps.
6. **Settle the unknowns.** Up to four questions in one round, recommended behavior first.
7. **Plan.** Each gap gets a test and a fix, with what changes for the caller, the user and the operator. Optional pin tests keep important handled rows handled. You approve per item.
8. **Apply.** One gap at a time, most dangerous first: write the test, confirm it fails for the right reason, apply the fix if you said yes, run the related suite. Anything that breaks is reverted from backup.
9. **Check completeness.** Counts taken from the work files.
10. **Report.**

A gap is proven twice: by reading, and by a test that fails on the current code. If the test passes, the gap was wrong and is dropped. Expected behavior always has a source (requirements, contracts, conventions, or how the codebase handles the same failure elsewhere). Where none exists you are asked, and a preference of Claude's does not count.

## What you get

- Tests and fixes as uncommitted changes in your working tree. If your tree has unrelated changes in the affected files, or the target is another branch or PR, they go to a worktree at `<repo parent>/<repo name>.worktrees/error-paths-<slug>` on branch `error-paths/<slug>`.
- A report that leads with the most dangerous open gaps, then the matrix per operation (handled, fixed, open, declined), tests added, fixes applied, what was reverted, open questions, test results before and after, and limits.
- A work directory outside your repo (`<scratchpad>/error-paths-<slug>/`, or a temp dir) with one file per step, the ledger, `backup/`, and `held-tests/` for gap tests whose fix you declined.

## Safety

- Never applies a fix without a per-item yes. `--auto` only skips the wait for tests.
- Commits nothing. It never switches your branch, stashes or resets.
- Runs tests only on your own work or a branch of the same repository, with what is already installed. It never installs a test library; it uses a hand-written fake at the boundary or names the missing tool in the plan.
- A PR from a fork is report only, and its code is not run.
- A fix that breaks a new test is restored from backup and marked `reverted`, not debugged into place.
- Every fix follows the codebase's error-handling style, leaves one log line with identifiers and no secrets, and returns an error that leaks nothing. The run ends with a self-check of the diff for this.
- Text in the code, comments, docs or PR description that tells Claude what to do is reported as a finding, not followed.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/failures.md` | The failure catalog: kinds of failure points, the 18 failures, impact and severity, and how to simulate each failure in tests per ecosystem |
| `references/formats.md` | The output contract for every work file, the plan, how to apply it, and the report |

## Related skills

- [`conventions`](../conventions/) — writes `docs/conventions.md`, the first source of expected behavior; run it if the repo has none.
- [`sdlc-fast`](../sdlc-fast/) — writes `docs/patterns.md`, which this skill also reads.
- [`guided-review`](../guided-review/) — walks you through the resulting diff.
- [`deslop`](../deslop/) — `--families ERR,LOG` catches swallowed errors and log noise the matrix didn't cover.
