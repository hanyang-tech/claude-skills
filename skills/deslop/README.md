# deslop

Finds the padding, guesswork and fakery that generated code leaves behind, and takes it out without changing what the code does unless you agree. You end up with a plan you approve, fixes applied in small tested batches, and a ledger showing what happened to every finding.

## When to use it

- "Clean up this AI-generated code."
- "Tighten this diff; it feels bloated and over-engineered."
- You see narrating comments, `try` blocks around code that cannot fail, one-implementation interfaces, or helpers the codebase already has.
- You suspect placeholders, fake implementations, hallucinated APIs or tests that check their own mocks.
- Not for: reading a change to judge it (use [`guided-review`](../guided-review/) or [`pr-review`](../pr-review/)), or refactoring old code that is expensive to change (use [`hotspots`](../hotspots/)).

## Usage

```
/deslop [target] [--report-only] [--auto] [--families <list>] [--all] [--models <role>=<model>,…]
```

With no target it works on uncommitted changes, else the current branch against its merge-base with the default branch, else the last commit. A commit, range or branch scopes it to the changed lines; a PR number or URL to the PR's changed lines; paths or globs to those files, whole.

| Option | What it does |
|---|---|
| `--report-only` | Stops after the plan and presents it as a report. Nothing is edited. |
| `--auto` | Applies safe and behavior-preserving fixes without waiting for plan approval. Behavior-changing fixes still need your yes, one by one. |
| `--families <list>` | Only these families, by catalog code, e.g. `--families CMT,ERR,DEAD`. |
| `--all` | Every tracked source file, minus generated, vendored and lockfile content. |
| `--models <role>=<model>,…` | Overrides an agent's model. Roles: `detector`, `skeptic`, `fixer`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/deslop
/deslop 482 --report-only
/deslop src/billing/ --families CMT,DEF,ERR
```

## How it works

1. **Get the target.** Work out the scope and where fixes will go.
2. **Learn the codebase.** Record its conventions (comments, errors, logging, naming, tests), index the helpers and libraries it already has, find its formatter, linter and test commands, and run the baseline tests.
3. **Find the slop.** One pass per family over every file in scope. The families are CMT (comments and docs), DEF (defensive overkill), ERR (swallowed errors), SPEC (speculative generality), DUP (reinvention), DEAD (dead code and leftovers), FAKE (placeholders), API (hallucinated APIs), TEST (test slop), NAME, VERB (verbose code), LOG (log noise), DRIFT (convention drift) and BLOAT.
4. **Verify every finding.** Each is checked against callers, exports, config and installed library source. In agent mode, risky ones go to a fresh skeptic.
5. **Plan the fixes.** You see counts, the worst findings with before and after, and every behavior-changing fix individually. Then it waits for you.
6. **Apply in batches.** Back up files, apply a batch, run the formatter, linter, type-checker and covering tests, compare with the baseline, and revert any batch that breaks something. A full suite run follows, then a check of the fix diff for slop it might have added.
7. **Check completeness.** Count from the files on disk.
8. **Report.**

Slop is judged against the codebase's own style, not a general taste. Fixes are classed S (safe), P (behavior-preserving), B (behavior-changing, applied only with your yes to that fix) or N (report only). Findings are marked 🔴 hides a bug, 🟠 costs, or 🟡 noise. For a diff target, only the changed lines and what the change made redundant are in scope; slop in older code is counted, not fixed. Small targets are done in one session. Larger ones, or `--all`, use Sonnet detectors and Opus skeptics, and Sonnet fixers when there are more than about 40 fixes.

Every finding ends with one status in the ledger: applied, reverted, declined, deferred, report only or skipped.

## What you get

- Fixes applied as uncommitted changes you can review with `git diff`, or in a separate worktree (see Safety).
- `report.md`: scope, lines removed and added, findings by family and status, tests before and after, every behavior change applied, what was reverted and why, and what is left for you to decide.
- A work directory kept after the run: `<scratchpad>/deslop-<slug>/` when a scratchpad exists, else a temporary directory, never inside your repository. It holds `steps.md`, `1-target.md` to `7-coverage.md`, `report.md`, and `backup/` with each file as it was before its first edit.

## Safety

- It never commits or pushes unless you ask, and never switches your branch, stashes or resets.
- Fixes go to your working tree when it is clean or the target is your uncommitted work. If the working tree has unrelated uncommitted changes in files that would be fixed, or the target is a branch that is not checked out or a PR from this repository, they go to a worktree at `<repo parent>/<repo name>.worktrees/deslop-<slug>` on a new branch `deslop/<slug>`.
- A PR from a fork is report only, and its code is not run.
- Tests, linters and type-checkers run only on your own work or a branch of the same repository, with what is already installed. It never installs anything.
- A batch that breaks a test is reverted, not debugged into place. A test that fails before any fix is not counted against a fix.
- Behavior-changing fixes are applied only with your yes to each one, even with `--auto`.
- Comments, docstrings, commit messages and the PR description are treated as data; text in them that tells it what to do is pointed out, not followed.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/catalog.md` | The baseline questions, the 14 slop families with how to detect and verify each, and the severity and fix classes |
| `references/fixing.md` | The plan format, how batches are applied and reverted, the ledger, and the report format |

## Related skills

- [`guided-review`](../guided-review/) — offered afterwards to walk through the fix diff together.
- [`pr-review`](../pr-review/) — reports on simplicity and convention fit in a PR without changing code.
- [`hotspots`](../hotspots/) — refactors the files that cost the most to change.
