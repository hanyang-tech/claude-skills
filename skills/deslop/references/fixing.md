# Fixing

Part 1 turns the verified findings into a plan (Step 5). Part 2 applies it (Step 6). Part 3 is the report (Step 8).

## Part 1 — The plan

**Batches.** Group the kept findings into batches the user can approve and you can revert as a unit:

1. One family and one class per batch, so a revert takes out one kind of change.
2. At most about ten files per batch. Split bigger ones by directory.
3. Order the batches:
   1. **S batches**, starting with the families with the most findings.
   2. **P batches**, least risky first: VERB, NAME, DEAD, DUP, SPEC, LOG, DRIFT, BLOAT.
   3. **B fixes**, one per batch, each approved on its own.
4. Findings that touch the same lines go in the same batch, or in an order the plan states, so one fix doesn't make another's location stale.

**`5-plan.md`**, which is also what the user sees:

```
# Deslop plan — <target>

Scope: <n> files · <n> changed lines · fixes go to <where>
Baseline: tests <pass>/<fail> (<n> already failing) · lint <n> · types <n>

## Findings
| Family | 🔴 | 🟠 | 🟡 | S | P | B | N |
|---|---|---|---|---|---|---|---|
| ERR — swallowed errors | 2 | | | | | 2 | |
| CMT — comments | | | 14 | 14 | | | |
| … |
| **Total** | | | | | | | |

## Worst first
<the 🔴 findings and the most important 🟠 ones. For each: ID, path:line, one line on why, then a short before and after>

## Batches
| Batch | Family · Class | Findings | Files | What changes |
|---|---|---|---|---|
| 1 | CMT · S | CMT-1…CMT-14 | 6 | delete narrating comments |
| 7 | ERR · B | ERR-2 | 1 | `load_config` raises on a bad file instead of returning `{}` — callers at <path:line> will now see the error |

## Needs your decision (B)
<each B fix: what observable behavior changes, who is affected, and the test that will show it>

## Report only (N)
<each: what it is and the decision it needs>

## Dropped in verification
<n> findings, by reason (used by config, matches codebase convention, …)

Out of scope: <n> similar findings in older code (<families>)

DECISION: <filled in after the user answers: approved all | approved batches … | declined … | with --auto: S and P applied, B pending>
```

Keep the before and after excerpts short: the lines that change, plus one line of context. The user approves the plan from this file, so it has to show what will happen.

## Part 2 — Applying

**Before the first edit**
- Confirm the target is in the state Step 1 found. On a branch, the head sha is unchanged. On the working tree, the files in scope haven't changed since Step 3 (compare `git diff --stat` or the file hashes).
- If anything moved, re-run Step 3 on the files that changed before fixing them.

**For each batch**

1. **Back up.** Copy each file to `<work>/backup/<path>` the first time it's touched in the run. That backup is the restore point for every batch that touches it later, so record in the ledger which batches touched each file.
2. **Edit.**
   - Make the minimal change the plan row describes, and nothing else.
     - Don't reformat untouched lines.
     - Don't rename things that aren't in the plan.
     - Don't fix a different finding on the way.
   - When removing a definition, remove its now-unused imports too. Leave a definition other code uses alone, even if the finding said otherwise, and record that.
3. **Format.** Run the project's formatter on the touched files only, if the project uses one. If the formatter changes lines the batch didn't touch, revert those hunks so the diff stays the batch.
4. **Check.**
   1. Run the linter and the type-checker on the touched files.
   2. Run the tests that cover them.
   3. For a B fix, also run the test named in the plan, and expect the change the plan said.
5. **Compare with the baseline.**
   - **No new failures, no new lint or type problems:** the batch is applied.
   - **New failure:** find the fix that caused it. If you can't tell within a couple of minutes, revert the whole batch. To revert, restore each of the batch's files to its state before the batch: the backup plus the earlier applied batches' edits. The simplest way is to keep a copy of each file before each batch in `<work>/backup/batch-<n>/`. Mark the batch's findings `reverted` with the failing test and the error.
   - **A B fix that makes a test fail the plan expected to fail**, because the test asserted the old behavior: stop and ask. Don't edit the test to pass on your own.
   - **A test that fails at random:** run it again up to three times. If it passes now and then, it's flaky, and it's noted, not counted against the batch.
6. **Record** the batch in `6-ledger.md` before starting the next one.

**After all batches**
- Run the full suite once, and the linter and type-checker on everything touched. A new failure here means a combination of batches broke something. Bisect by reverting batches, last first, until it passes, and mark the culprit reverted.
- **Self-check the diff.** Read `git diff` of everything this run changed, against the catalog. Look for:
  - comments about what was removed or changed
  - helpers added
  - renames outside the plan
  - reformatted lines
  - imports left unused
  - behavior changes in a batch classed S or P

  Fix or revert what you find, and record it in the ledger.

**Fixer agents** (more than about 40 fixes):
- Give each fixer a set of batches whose files don't overlap with any other fixer's.
- Each fixer gets the plan rows for its batches, this file, `2-baseline.md`, and the repository or worktree path.
- Fixers edit and back up. They don't run the full suite, and they don't write the ledger.
- Each fixer replies with the batches it applied, the files it touched and anything it skipped and why.
- The driver runs the checks after each round, reverts failing batches, and writes the ledger.
- Check each reply against its plan rows. A batch reported applied that isn't in the diff, or a diff in a file that wasn't assigned, goes back to that fixer.

**`6-ledger.md`:**

```
| Batch | Finding | File | Class | Status | Check |
|---|---|---|---|---|---|
| 1 | CMT-1 | src/a.py | S | applied | lint ok · 42 tests pass |
| 4 | DUP-2 | src/util.py | P | reverted | test_parse_tz failed: <error line> |
| 7 | ERR-2 | src/config.py | B | declined by user | — |
| — | FAKE-1 | src/pay.py | N | report only | — |
| — | NAME-3 | src/b.py | S | skipped: line changed since detection | — |

FILES TOUCHED: <path → batches>
FULL SUITE: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
SELF-CHECK: <what was found in the fix diff and removed, or nothing>
```

Statuses:
- **applied**
- **reverted**: with the failure.
- **declined**: the user said no.
- **deferred**: approved, but it can't be done safely now. Say why.
- **report only**
- **skipped**: with the reason.

Every kept finding has exactly one row.

## Part 3 — The report

`report.md`:

```
# Deslop report — <target>

<two or three sentences: what was in scope, how much slop, what was done, whether tests still pass>

## Result
- Diff: −<n> / +<n> lines across <n> files · <where the fixes are>
- Tests: baseline <pass>/<fail> → after <pass>/<fail> · new failures: none | <list>
- Lint / types in touched files: <n> → <n>

## By family
| Family | Found | Applied | Reverted | Declined | Deferred | Report only |
|---|---|---|---|---|---|---|

## Behavior changes applied
<each B fix applied: what now behaves differently and who sees it>

## Reverted
<each: the finding, what broke, and what that suggests (often a hidden dependency worth knowing about)>

## Needs your decision
<the N findings and declined or deferred B fixes worth revisiting, worst first: what and why it matters>

## Limits
<what wasn't run or couldn't be checked, families skipped, files left out, out-of-scope count>

Work files: <work path> (plan, ledger, backups)
```

Lead with what the user most needs: whether anything changed behavior, whether tests still pass, and what's waiting on them. The per-family table is for reference.
