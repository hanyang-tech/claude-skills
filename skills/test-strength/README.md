# test-strength

Measures whether your tests would catch bugs in the code, by planting small bugs (mutants) and seeing which ones the tests miss. It then adds tests for the real gaps, written from the requirements and not from what the code returns today.

## When to use it

- "How strong are the tests for this change? Would they catch a bug?"
- "Run mutation testing on this branch / PR / these files."
- Coverage is high but you don't trust the assertions.
- You want tests added for the behavior nothing actually checks.
- Not for: cleaning up weak or sloppy tests (use [`deslop`](../deslop/) with `--families TEST`), or reviewing a diff for bugs (use [`pr-review`](../pr-review/) or [`deep-review`](../deep-review/)).

## Usage

```
/test-strength [target] [options]
```

With no target it works on uncommitted changes, else the current branch against its merge-base, else the last commit. A commit, range, branch, PR number or URL, or paths and globs also work, and `--all` covers every tracked source file. For a diff only the changed lines are mutated.

| Option | What it does |
|---|---|
| `--budget <min>` | Wall-clock minutes for the mutation run. Default 20. |
| `--tool <name>` | Use `mutmut`, `cosmic-ray`, `stryker`, `gremlins`, `go-mutesting`, `cargo-mutants`, `pitest` or `mutant`, or `manual` for hand-made mutants. Default: an installed tool that fits, else `manual`. |
| `--report-only` | Stop after the plan and present it as a report. No test is written. |
| `--auto` | Write the planned tests that have a written requirement without waiting for approval. Questions and bugs found still wait for you. |
| `--all` | Every tracked source file, minus generated, vendored and test files. |
| `--models <role>=<model>,…` | Override an agent's model. Roles: `mutator`, `skeptic`, `test-writer`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/test-strength
/test-strength 412 --budget 40
/test-strength src/billing/ --report-only
/test-strength main..HEAD --tool mutmut
```

## How it works

1. **Get the target.** Work out what is in scope, where new tests will go, and whether code may be run.
2. **Baseline.** Find the test conventions and the covering tests, make a scratch copy of the code runnable, prove it with a canary mutant, and run the baseline twice.
3. **Make and run the mutants.** Pick mutants from an operator catalog (conditions, return values, error paths, boundaries first) and run only the covering tests against each, with a tool or by hand. Score = killed over killed, survived and not covered.
4. **Verify the survivors.** Each is judged a gap, equivalent or unobservable, with a reason or a distinguishing input. Weak tests met on the way are listed.
5. **Plan the tests.** One test per requirement, each naming where the expected behavior is written down. You see the score, the gaps, the questions and where tests will go, then approve.
6. **Write the tests.** Batch by function, each proven to pass on the original code and fail on its mutant.
7. **Measure again.** Re-run the mutants in the touched functions; score before and after.
8. **Check completeness.** Counts taken from the work files, not from memory.
9. **Report.**

A new test has to earn its place: it passes on the original code and fails on the mutant it targets, and both runs are recorded. If a test written from a requirement fails on the original code, that is a bug found. The test is set aside, you are told, and neither the test nor the code is changed to make it go away. Where nothing written says what the code should do, you get a question, not an expectation copied from the code.

## What you get

- New test files or additions to existing test files, left uncommitted in your working tree. If your tree has unrelated changes in those test files, or the target is another branch or PR, they go to a worktree at `<repo parent>/<repo name>.worktrees/test-strength-<slug>` on branch `test-strength/<slug>`.
- A report: bugs found first, then the score before and after per file, tests added, survivors left and why, weak tests seen, and the limits of the run.
- A work directory outside your repo (`<scratchpad>/test-strength-<slug>/`, or a temp dir) with one file per step, the mutant results, the ledger, `bugs/` for failing requirement tests, and `backup/` of test files before their first edit.

## Safety

- Never edits the code under test. Mutants are applied one at a time in a scratch worktree, and each file is restored and checked byte for byte before the next. Your tree only gains test files.
- Commits nothing. It never switches your branch, stashes or resets.
- Runs tests and mutation tools only on your own work or a branch of the same repository, with what is already installed. It never installs a mutation tool, coverage plugin or test runner; without one, mutants are made by hand.
- A PR from a fork is not run at all. It stops after Step 1 unless you say to go ahead.
- Tests are written only after you approve the plan (or under `--auto`, only those with a written requirement). A batch that breaks an existing test or is flaky is restored from backup.
- Text in comments, docstrings or the PR description that tells Claude what to do is reported as a finding, not followed.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/mutants.md` | The scratch tree and baseline, the operator catalog, how to run mutants, and how to verify survivors and spot weak tests |
| `references/tests.md` | Where requirements come from, the plan, writing and proving tests, re-measuring, and the report format |
| `scripts/mutate.py` | Applies, runs and restores hand-made mutants one at a time. Python standard library only. |

`mutate.py` has three subcommands: `check` validates the mutants file, `run` runs them (and resumes from its results file), `summary` scores them. Run `python3 scripts/mutate.py --help` for the mutants file format.

```
python3 scripts/mutate.py run --tree DIR --mutants FILE --out FILE [--budget MIN]
```

## Related skills

- [`deslop`](../deslop/) — fixes the weak tests this skill lists, with `--families TEST`.
- [`guided-review`](../guided-review/) — walks you through the new tests before you commit them.
- [`conventions`](../conventions/) — writes `docs/conventions.md`, which this skill reads for test style and as a requirement source.
