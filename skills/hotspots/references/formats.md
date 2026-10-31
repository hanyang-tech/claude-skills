# Formats

The output contract for every work file, in step order, and the procedure for applying steps. Step 2 writes the ranking, Step 3 the baseline and diagnosis, Step 4 the verification, Step 5 the plan, Step 6 the safety net, Step 7 the ledger (by Part 2), Step 8 the measurements and Step 10 the report.

## Contents

- Part 1 — Ranking, baseline, diagnosis and verification
- Part 2 — The plan and applying it
- Part 3 — Measuring and the report

---

## Part 1 — Ranking, baseline, diagnosis and verification

**Output contract for `2-ranking.md`:**

```
Ranked: <n> source files · window --since <value> · <n> commits · history <n> days
Complexity: proxy (indent) | <tool and command>
Young history: no | yes: <days, commits> — chose on complexity and bug fixes

| Rank | Path | Commits | Bug fixes | Lines | Longest fn | Max nest | Why it ranks |
|---|---|---|---|---|---|---|---|
| 1 | src/orders/service.py | 41 | 9 | 812 | 140 | 6 | changes weekly, 9 fixes, one 140-line function |
(top ten; a high-churn, low-complexity file says "cheap: registry" in Why)

COUPLING
| Pair | Together | Share | Across modules | Note |
|---|---|---|---|---|

CHOSEN: <paths> · by the user | by --auto (top <n>) | named paths
```

**Output contract for `3-baseline.md`:**

```
WRITTEN RULES: docs/conventions.md <yes | no> · docs/patterns.md <yes | no> · CLAUDE.md <yes | no>
<the rules that bear on the chosen files, one line each, with their IDs>

TOOLS
| Tool | Command | Result on chosen files |
|---|---|---|
(formatter, linter, type-checker, tests, coverage, complexity; "not installed" where absent)

BASELINE TESTS
Targeted: <command> · <n> passed · <n> failed · <n> skipped
Full suite: <command> · <counts> · <duration> | not run: <why>
Already failing: <test ids, or none>

COVERAGE
| File | Lines | Branches | Measured by | Uncovered public functions |
|---|---|---|---|---|
| src/orders/service.py | 61% | 44% | pytest-cov | `apply_discount`, `split_shipment` |
```

**Output contract for `3-diagnosis.md`** (or `3-diagnosis-<file slug>.md` from a diagnoser):

```
## <path>
Read: whole file (<n> lines) · callers <n> in <files> · tests <files> · coupled with <files>
History: <n> commits, <n> bug fixes in the window · oldest <date>

RESPONSIBILITIES
1. <what> — lines <a-b>, <names>
2. …

SIGNALS
| Signal | Found | What was checked |
|---|---|---|
| LONG | 2 | every function over 40 lines |
| RESP | 1 | import groups, function clusters, callers per group |
| NEST | 1 | |
| DUP | 0 | `rg` for the discount calculation, jscpd not installed |
| COUP | 1 | pair with src/orders/pricing.py |
| STATE | 0 | module-level names, writers |
| NAME | 0 | |
| MIX | 1 | |
| TYPE | 1 | `rg -n "order.kind"` |

FINDINGS
### <ID: SIGNAL-n, e.g. LONG-1> <one-line claim>
- Where: <path:line-line>
- Numbers: <length, depth, branches, copies, coupling count>
- History: <commits that touched these lines, bug fixes marked, from git log -L>
- Cost: <what this makes hard or risky to change, concretely>
- Steps: <refactorings from the catalog, each with its class (P | B | N) and its precedent in this codebase (path:line), or "no precedent">

### <next finding>
```

**Output contract for `4-verification.md`:**

```
FINDINGS
| ID | Claim | Checked how | Result |
|---|---|---|---|
| LONG-1 | `checkout` does four jobs | read whole; sections at 120, 160, 210, 240 share only `order` | Confirmed |
| DUP-1 | discount calc duplicated | copies differ on negative totals (path:line) | Dropped: different edge case |

STEPS
| Step | Refactoring | Why it keeps behavior | Skeptic | Class |
|---|---|---|---|---|
| S3 | extract `price_lines` from `checkout` | pure block, reads `order` and `rates`, returns totals; no early exit | PRESERVES | P |
| S5 | lookup table for `order.kind` | old `else` raises `ValueError`; table miss raises `KeyError` | CHANGES: error type | B |

ADDED TO THE SAFETY NET: <cases from RISK answers, or none>
RECLASSIFIED: <step: old → new class and why, or none>
```

---

## Part 2 — The plan and applying it

**Plan rules.**
1. One sequence per file. Coupled files that a step changes together share a sequence.
2. Order: the safety net (S0), then steps inside functions (rename locals, guard clauses, extract function), then between functions (parameter object, lookup table, pass state as parameter, separate I/O), then between files (move, split module). Later steps build on earlier ones.
3. One refactoring per step. A step that touches more than a few hundred lines is split.
4. Each step names the tests that check it and the steps it depends on, so a revert can skip what depends on it.
5. B steps are listed separately, each with what changes and who is affected, and each needs its own yes.

**Output contract for `5-plan.md`**, which is also what the user sees:

```
# Hotspots plan — <repo> <scope>

Chosen: <paths> · changes go to <the working tree | worktree path and branch | nowhere: report only>
Baseline: tests <pass>/<fail> (<n> already failing) · lint <n> · types <n>

## <path> — why it costs
<two or three lines: the confirmed findings, with the history evidence>
Safety net: coverage <n>% lines · <n> public functions to characterize: <names>

| Step | Refactoring | Where | Class | Checked by | Depends on |
|---|---|---|---|---|---|
| S0 | characterization tests for `apply_discount`, `split_shipment` | tests/orders/test_service_characterization.py | — | runs green on unchanged code | — |
| S1 | guard clauses in `checkout` | service.py:120-190 | P | test_service.py, characterization | S0 |
| S2 | extract `price_lines` | service.py:160-205 | P | same | S1 |

Before → after (for the bigger steps): <a short excerpt of each>

## Needs your decision (B)
<each: the step, what observable behavior changes, who is affected (callers at path:line, external users), the test that shows it>

## Report only (N)
<each: the redesign, the options and what each would cost>

## Dropped in verification
<n> findings and <n> steps, by reason

DECISION: <filled in after the user answers: approved all | approved <steps> | declined <steps> | --auto: P applied, B pending>
```

Keep excerpts to the lines that change, plus one line of context.

**Applying.**

Before the first edit:
- Confirm the files are as Step 3 read them: the same head sha, and `git diff --stat` or file hashes unchanged. If something moved, diagnose that file again before editing it.
- In a worktree, create it with `git worktree add -b hotspots/<slug> <path> HEAD` and work only there.

For each step:
1. **Back up.** Copy each file to `<work>/backup/<path>` the first time the run touches it, and to `<work>/backup/step-<n>/<path>` before this step.
2. **Edit.** Make the one refactoring the step describes. Don't reformat untouched lines, rename what the plan doesn't rename, or fix anything else on the way, including a suspected bug.
3. **Format** the touched files with the project's formatter. If it changes lines the step didn't touch, revert those hunks.
4. **Check.** Lint and type-check the touched files. Run the step's tests and all characterization tests for the file.
5. **Compare with the baseline.**
   - No new failures and no new lint or type problems: applied.
   - A new failure: restore the step's files from `backup/step-<n>/`, mark the step reverted with the failing test and its error line, and mark the steps that depend on it skipped. Don't debug the refactoring into place.
   - A flaky test: run it up to three times. If it passes sometimes, note it and don't count it against the step.
   - A B step whose expected test change appears: stop and ask before editing that test.
6. **Record** the step in the ledger before starting the next.

After the last step:
- Run the full suite once, and the linter and type-checker on everything touched. A new failure means a combination broke something. Revert steps, last first, until it passes, and mark the culprit reverted.
- Read the whole diff for slipped-in behavior: changed literals, conditions, ordering, error types or messages, log lines, public names. Also look for comments narrating the refactor and reformatted lines. Fix or revert, and record it.

**Output contract for `7-ledger.md`** (refactorers write `7-ledger-<group>.md` in the same shape):

```
| Step | File | Refactoring | Class | Status | Check |
|---|---|---|---|---|---|
| S0 | tests/orders/test_service_characterization.py | characterization tests (12) | — | applied | 12 pass on unchanged code, twice |
| S2 | src/orders/service.py | extract `price_lines` | P | applied | lint ok · 58 tests pass |
| S4 | src/orders/service.py | parameter object `ShipTo` | P | reverted | test_split_shipment: KeyError 'zip' |
| S5 | src/orders/service.py | lookup table for kind | B | declined by user | — |
| S6 | src/orders/service.py | move `ShipTo` to models.py | P | skipped: depends on S4 | — |

FILES TOUCHED: <path → steps>
FULL SUITE: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
SELF-CHECK: <what the diff read found and how it was handled, or nothing>
```

Statuses: **applied**, **reverted** (with the failure), **skipped** (with the reason), **declined** (the user said no), **deferred** (approved but not safe now, with why), **report only**. Every step in the plan has exactly one row.

---

## Part 3 — Measuring and the report

**Output contract for `6-safety-net.md`:**

```
| Public function | File | Covered before | Characterization tests | Covered after |
|---|---|---|---|---|
| `apply_discount` | src/orders/service.py | no | 7 (incl. negative total, empty cart) | yes, 100% branches |

SUSPECTED BUGS PINNED
- <test id>: <input> returns <value>; looks wrong because <reason>. Pinned as is.

Runs on unchanged code: <n> pass, twice · nondeterminism found: <none | fixed by …>
Coverage: <file>: <before>% → <after>% lines, <before>% → <after>% branches | read, not measured
```

**Output contract for `8-measure.md`:**

```
| File | Lines | Indent | Functions | Longest fn | Max nest | <tool metric> | Responsibilities |
|---|---|---|---|---|---|---|---|
| src/orders/service.py before | 812 | 2140 | 31 | 140 | 6 | CC max 24 | 4 |
| src/orders/service.py after | 640 | 1390 | 38 | 46 | 3 | CC max 9 | 2 |
| src/orders/pricing_rules.py new | 120 | 210 | 6 | 30 | 2 | CC max 5 | 1 |
| **Total / worst** before → after | 812 → 760 | | | 140 → 46 | 6 → 3 | 24 → 9 | |

Method: hotspots.py --measure (same for both) · <tool and command, if used>
```

A refactoring that splits a file can raise total lines a little. The longest function, the deepest nesting and the responsibilities per file are what should fall.

**Output contract for `report.md`:**

```
# Hotspots report — <repo> <scope>

<two or three sentences: what was ranked, which files were worked on and why, what changed, whether tests still pass>

## Result
- Files: <n> refactored · <n> steps applied of <n> planned · <where the changes are>
- Tests: baseline <pass>/<fail> → after <pass>/<fail> · new failures: none | <list>
- Characterization tests added: <n> in <files>
- Lint / types in touched files: <n> → <n>

## Before and after
<the totals rows of 8-measure, one per file>

## Why these files
<per file: rank, numbers, the confirmed costs with their history evidence>

## Suspected bugs pinned
<each: the test, the input, what it does, why it looks wrong. Not fixed.>

## Behavior changes applied
<each B step applied: what now behaves differently and who sees it, or none>

## Reverted and skipped
<each: the step, what broke, and what that suggests about hidden dependencies>

## Needs your decision
<declined or deferred B steps, report-only redesigns, the next hotspots in the ranking>

## Limits
<young history, proxy instead of a complexity tool, coverage read not measured, tests not run, files left out>

Work files: <work path> (ranking, plan, ledger, backups)
```

Lead with what the user most needs: whether behavior changed, whether tests still pass, and the suspected bugs waiting on them. The tables are for reference.
