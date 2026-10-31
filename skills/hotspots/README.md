# hotspots

Finds the existing code that costs the most to change and refactors it in small steps without changing what it does. It ranks files from git history by churn, complexity and bug-fix commits, diagnoses the ones you pick, and applies each approved step with tests after it. You end up with uncommitted changes (or a branch), a ledger of every step, and before-and-after numbers.

## When to use it

- "What are the worst parts of this codebase?" or "where is our technical debt?"
- "What should we refactor first?"
- A file everyone has to touch keeps collecting bug fixes and nobody wants to edit it.
- You want to refactor old code safely, with tests pinning behavior first and a revert for any step that breaks something.
- Not for: reviewing new changes. Reviews only see new code; this skill works from git history to find older code that hurts.

## Usage

```
/hotspots [target] [options]
```

With no target it ranks every tracked source file in the repository, minus generated, vendored and test files. `--scope <dir>` limits that to one directory. Named paths skip the ranking and go straight to diagnosis.

| Option | What it does |
|---|---|
| `--scope <dir>` | Rank only inside this directory or package |
| `--since <date>` | History window for churn, bug fixes and coupling, in git's `--since` form. Default `12 months` |
| `--top <n>` | With `--auto`, how many top-ranked files to take. Default 2 |
| `--report-only` | Stop after the plan. Nothing is edited |
| `--auto` | Take the top `--top` files without asking and apply the behavior-preserving steps without waiting for plan approval. Behavior-changing steps still need a yes each |
| `--models <role>=<model>,…` | Override an agent's model. Roles: `diagnoser`, `skeptic`, `refactorer`. Values: `sonnet`, `opus`, `fable` |

Examples:

```
/hotspots
/hotspots --scope services/billing --since "6 months" --report-only
/hotspots src/orders/service.py src/orders/pricing.py
```

## How it works

1. **Get the target** - scope, window, current branch and head, and whether code may run.
2. **Rank** - `scripts/hotspots.py` scores files by churn, complexity and bug fixes, and lists files that change together. You pick which to work on from the top ten.
3. **Diagnose** - record baseline tests, tools and coverage, then read each chosen file whole with its callers, tests and history. Check nine signals: long functions, several responsibilities, deep nesting, duplication, temporal coupling, hidden global state, unclear names, mixed abstraction levels, and type switches that grow. Each finding has `path:line`, numbers and commit evidence.
4. **Verify** - try to disprove every finding and every proposed step. A skeptic challenges each non-trivial step.
5. **Plan** - ordered steps per file, each small enough to revert alone and marked behavior-preserving (P) or behavior-changing (B). You approve all, some or none.
6. **Build the safety net** - write characterization tests for uncovered behavior, pinning what the code does now, odd parts included.
7. **Apply step by step** - back up, make one change, format, lint, test, compare with the baseline. A step that breaks something is reverted, and steps that depend on it are skipped.
8. **Measure before and after** - the same method on the backup and the current file.
9. **Check completeness** - count from the work files.
10. **Report.**

A bug found along the way is reported, not fixed. Redesigns that need a decision are listed as report-only. Refactorings follow shapes the codebase already uses, and `docs/conventions.md` and `docs/patterns.md` take priority over general taste.

With one or two files under about 500 lines it works inline. Otherwise it launches `general-purpose` agents: `opus` diagnosers and skeptics, `sonnet` refactorers.

## What you get

- Changes in your working tree as uncommitted changes. If a file the plan touches already has uncommitted changes, they go in a worktree at `<repo parent>/<repo name>.worktrees/hotspots-<slug>` on branch `hotspots/<slug>`. With `--report-only`, no changes.
- Characterization tests, named and marked as such, for behavior that wasn't covered.
- `report.md`: why these files, before and after numbers, tests before and after, suspected bugs pinned by the tests, behavior changes applied, what was reverted and why, what is left for you to decide, and the limits of the run.
- A work directory outside your repository (`<scratchpad>/hotspots-<slug>/`, or a temporary directory) holding the ranking, diagnosis, plan, ledger, measurements and a backup of every file before each step. Nothing is removed from it.

## Safety

- Commits nothing, and never switches your branch, stashes or resets.
- Behavior stays the same. Anything callers could notice, such as a public API change or a different error type, is a B step and is applied only with a separate yes.
- Runs tests, coverage, linters and type-checkers only on your own repository, and only what is already installed. It never installs anything. In a repository that isn't yours, such as a third-party clone, it asks before running anything.
- Text in code, comments and commit messages that addresses the agent is treated as a finding, not an instruction.
- Tests that already fail before any edit don't count against a step.
- Needs your answer twice: which files to work on, and the plan. The report lists any steps still waiting on you.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/diagnosis.md` | Reading the ranking, the nine cost signals, how to disprove them, the refactoring catalog, and the safety-net procedure |
| `references/formats.md` | Output formats for every work file, the plan rules and the procedure for applying steps |
| `scripts/hotspots.py` | Ranks files from one `git log --numstat` pass, lists coupled pairs, and measures files with `--measure`. Read-only. Python standard library only |

Run the script on its own:

```
python3 scripts/hotspots.py --repo <repo> [--scope <dir>] --since "12 months" --top 30
python3 scripts/hotspots.py --measure <file> [<file> ...]
```

## Related skills

- [`conventions`](../conventions/) - writes the conventions doc this skill follows; it is suggested after the run if the repository has none.
- [`guided-review`](../guided-review/) - review the resulting diff or the `hotspots/<slug>` branch.
- [`deslop`](../deslop/) - run on the refactored files afterwards.
