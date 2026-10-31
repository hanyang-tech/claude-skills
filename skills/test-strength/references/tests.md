# Tests

Part 1 says where expected behavior comes from, and Part 2 turns the gaps into a plan (both Step 5). Part 3 writes and proves the tests and keeps the ledger (Step 6). Part 4 measures again (Step 7). Part 5 is the report (Step 9). Each part ends with the output contract of the file it writes.

## Part 1 — Where requirements come from

A test checks a requirement. The code under test is the thing being checked, so it can't also be the source of what it should do. A test whose expected value was copied from running the function passes on every bug that was already there, and kills only the mutants that change today's output, which proves nothing about whether today's output is right.

Look for the expected behavior in this order, and cite the first that answers:

| Source | Where | Cite as |
|---|---|---|
| A requirement the user gave | the conversation, a spec file they named | `user, <date>` or `<path>` |
| A spec, design doc or ADR | `docs/`, `specs/`, `adr/`, linked from the PR | `<path>:<line>` with a short quote |
| The issue or ticket | linked from the PR or commit message, opened with `gh issue view` | `#<n>` with a short quote |
| The PR description or commit message | `gh pr view`, `git log` | `PR #<n>` or `<sha>` with a short quote |
| The function's own contract | its docstring, JSDoc, doc comment, declared errors (`Raises:`, `@throws`), type signature (`Optional`, `Result`, non-null) | `<path>:<line>` with a short quote |
| Published behavior | README, API docs, OpenAPI or JSON schema, CLI help text, error message catalog | `<path>:<line>` |
| The codebase's rules | `docs/conventions.md`, `docs/patterns.md` (e.g. "money in integer minor units", "not found raises `NotFoundError`") | `CONV-<n>` or `PAT-<n>` |
| Inferred, to confirm | how callers use the result (a caller that branches on `None` expects `None` for missing), a sibling test that states the rule for the neighboring case | `inferred: <path>:<line>`, and shown to the user as a question |
| Nobody says | — | a question for the user |

Rules:
- **Never** run the function to get the expected value, and never read the expected value off the original line the mutant changed.
- **Inferred sources are questions.** The plan shows them, and the test is written once the user confirms or with `--auto` only if the user already answered.
- **When a source and the code disagree,** the source wins for the test. If the test then fails on the original code, that's a bug found (Part 3), and the user decides.
- **When two sources disagree,** neither wins. It's a question, with both quoted.
- **A boundary needs the boundary stated.** "Rejects negative amounts" says 0 is accepted. "Amount must be positive" says 0 is rejected. If the source doesn't settle the boundary value, it's a question.

**Questions** go to the user in one round, at most four, the most consequential first: the ones with the most gaps behind them, then those on error paths and money, auth or data. Each states the behavior in question, the input, the options, and what the code does now, labelled as what the code does, not as the answer. The rest are listed in the plan and their gaps are deferred.

## Part 2 — The plan

Group the gaps from `4-verification.md` by function. For each function, one test per requirement, and one requirement can kill several mutants: "an empty cart totals 0" kills the RET, GUARD and LOOP mutants on `total`. For a not-covered function, the tests describe its main requirements first, then the boundaries and error paths the mutants point at.

Describe each test as the behavior it checks, in words the requirement uses, not as the mutant it kills: "a 0 amount is accepted and returns 0", not "test for M14".

**`5-plan.md`**, which is also what the user sees:

```
# Test-strength plan — <target>

Scope: <n> files · <n> changed lines with logic · tests go to <where>
Baseline: <n> covering tests · <pass>/<fail> · excluded: <n> failing, <n> flaky · <s>s per run
Mutation: <tool | manual> · <n> run of <n> chosen (<n> not run: budget) · canary killed

## Score now
| File | Mutants | Killed | Timeout | Survived | Not covered | Equivalent | Score |
|---|---|---|---|---|---|---|---|

## Gaps by function
### `parse_amount` — src/money.py:10-30 · 3 survived, 1 not covered
| # | Test to add (the requirement) | Source | Kills |
|---|---|---|---|
| T1 | a 0 amount is accepted and returns 0 | docstring src/money.py:12 "Raises ValueError if the amount is negative" | M14 (`<` → `<=` at :18) |
| T2 | "1,000.50" parses to 100050 minor units | CONV-4 money in integer minor units | M15, M16 |
| T3 | ? | **Q1** | M17 |

## Questions
Q1. What should `parse_amount("")` do: raise ValueError, or return 0? The code currently returns 0. <the options, as asked>

## Not gaps
Equivalent: <ID: the rule and why it holds here> · Unobservable: <ID: what differs and why no caller sees it>

## Weak tests seen
| Test | Pattern | Evidence |
|---|---|---|
(listed for /deslop --families TEST; not fixed here)

## Not run
<n> mutants the budget didn't reach, by file. A re-run with a bigger --budget resumes them.

DECISION: <filled in after the user answers: approved all | approved T1, T2 | declined T3 | Q1 answered: … | with --auto: written-source tests written, questions pending>
```

## Part 3 — Writing and proving

### Write in the codebase's style

Follow `2-baseline.md`'s test conventions, and `docs/conventions.md` or `docs/patterns.md` where they speak to tests:
- Put the test in the existing test file for that module, next to the tests of the same function. Create a file only where the codebase has none for the module, named and placed the way the others are.
- Use the existing fixtures and factories. Mock only what the codebase mocks, usually the outside systems.
- Parametrize where the codebase parametrizes, and name the test for the behavior: `test_zero_amount_is_accepted`, `it("accepts a zero amount")`.
- Test through the public function, not private helpers or attributes. If a mutant can only be killed by reaching into internals, go back to Step 4: it's probably unobservable.

### Make it kill its mutant

| Mutant | What the test needs |
|---|---|
| BND, OBO | the boundary value itself, and the first and last elements, with the exact expected result |
| NEG, LOG | inputs for both outcomes, and for LOG an input where exactly one side is true |
| RET | an assertion on the value, not only that it exists or isn't null |
| STMT, AWAIT | an assertion on the effect: the state, the stored row, the output, or the call to the outside system, after the work has finished |
| RAISE, GUARD | the bad, empty or missing input, and the specific error, with its message where the codebase checks messages (`pytest.raises(ValueError, match=…)`, `toThrow(…)`, `errors.Is`) |
| CONST, ARITH | an input where the constant or operator changes the result visibly, so not 0 or 1 |
| LOOP, ARGS | at least two different elements, or two arguments that differ |

### Prove it

For each new test:

1. **On the original code,** where the tests go, run the new test alone. It must pass. Run it a second time to catch a flaky test.
2. **On its mutant.** Copy the test file into the scratch tree at the same path. Write a one-line mutants file with the target mutant and a `cmd` that runs only the new test, then `mutate.py run` it. The status must be `killed`, and the tail must show the new test failing on an assertion about the behavior. An import error, a fixture crash or a collection error doesn't count.
3. Keep the test in the scratch tree, so Step 7 measures with it.

**It fails on the original code.** The requirement says one thing and the code does another. That's a bug found:
- Take the test out of the user's tree, and save it to `<work>/bugs/<function>-<n>.<ext>` with the failing output beside it.
- Stop the run and tell the user: the requirement, quoted with its source, the test, the input, what was expected, and what happened.
- Ask whether to keep the test as failing, or as an expected failure the way the codebase marks one (`pytest.mark.xfail(reason=…, strict=True)`, `it.failing`, `t.Skip` with a reason), to drop it, or to leave it for a separate fix.
- Don't change the test until it passes, and don't fix the code. The ledger status is `bug found`, whatever the user picks.
- Carry on with the other batches after the answer, with `--auto` too.

**It passes on its mutant.** The test doesn't check what the mutant broke. Strengthen it once, still from the requirement. If the requirement itself can't tell the two versions apart, the gap is in the requirement: mark the mutant `deferred: requirement doesn't distinguish`, and say what would need deciding.

### Batches

1. One function's tests per batch.
2. Before the first edit to a test file, copy it to `<work>/backup/<path>`. Record new files.
3. After writing and proving the batch, run every covering test of the touched files, with the new tests, and compare with the baseline.
4. A batch that breaks an existing test, or whose new tests fail now and then, is reverted: restore the backed-up files, delete the new ones, and mark its rows `reverted` with the failure. Don't debug it into place.
5. Write the batch to the ledger before the next one.

After all batches, run the covering tests of everything in scope once more, and check `git status`: only test files changed in the user's tree.

**Test-writer agents** get their plan rows, this file, `2-baseline.md`, the path of `scripts/mutate.py`, their own scratch tree, and test files no other writer touches. They write and prove, and reply with the tests written, both proof results per test, and any bug found, which the driver takes to the user. They don't write the ledger.

**`6-ledger.md`**, one row per mutant that survived or was not covered in Step 3:

```
| Mutant | Function | Where | Change | Step 3 | Status | Test | On original | On mutant | Batch |
|---|---|---|---|---|---|---|---|---|---|
| M14 | parse_amount | src/money.py:18 | `<` → `<=` | survived | test added | tests/test_money.py::test_zero_amount_is_accepted | pass ×2 | killed: AssertionError expected 0 | 1 |
| M15 | parse_amount | src/money.py:24 | RET → None | survived | killed by new test | test_thousands_separator (T2) | — | killed | 1 |
| M17 | parse_amount | src/money.py:27 | GUARD removed | survived | deferred: needs requirement | — | — | — | — |
| M19 | parse_amount | src/money.py:55 | log text | survived | unobservable | — | — | — | — |
| M22 | refund | src/pay.py:80 | RAISE removed | not covered | bug found | <work>/bugs/refund-1.py | FAILS: no error raised for a refund above the charge | — | 3 |

FILES TOUCHED: <test file → batches · new files>
FULL RUN: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
USER'S TREE: <git status --short: only test files>
SELF-CHECK: <slop found in the new tests and removed, or nothing>
```

Statuses, one per row:
- **test added:** a test written for this mutant kills it.
- **killed by new test:** a test written for another mutant kills this one too.
- **equivalent** and **unobservable:** from Step 4, with the reason in the verification file.
- **bug found:** the requirement test failed on the original code.
- **declined:** the user said no.
- **deferred: needs requirement**, or **deferred: requirement doesn't distinguish.**
- **reverted:** with the failure.
- **skipped:** the line changed since Step 3, or similar, with the reason.

## Part 4 — Measuring again

Re-run every Step 3 mutant in each function that got a test, with the same IDs and lines, not only the ones targeted. A new test can kill more, and a strengthened fixture can change other outcomes. The covering-test commands now include the new tests. The code hasn't changed, so the mutants still apply. Re-run `mutate.py check` to be sure.

**`7-after.md`:**

```
Functions re-measured: <n> · mutants re-run: <n> · command: <…>

| File | Function | Before | After | Survivors left |
|---|---|---|---|---|
| src/money.py | parse_amount | 2/6 (33%) | 5/6 (83%) | M17 deferred |
| **Total** | | <x>% | <y>% | <n> |

Scores are (killed + timeout) / (killed + timeout + survived + not covered − equivalent).

SURVIVORS LEFT
| Mutant | Why |
|---|---|
| M17 | deferred: Q1 unanswered |
| M19 | unobservable: log wording |
```

A mutant that was killed before and survives now means a new test or fixture changed what the old tests saw. Look into it before reporting.

## Part 5 — The report

**`report.md`:**

```
# Test-strength report — <target>

<two or three sentences: the score before and after, how many tests were added, bugs found, and whether the existing tests still pass>

## Bugs found
<each: the requirement, quoted with its source · the input · expected vs. actual · the test, at <work>/bugs/… or in the tree · what the user decided>
<or "None.">

## Score
| File | Mutants | Before | After | Survivors left |
|---|---|---|---|---|

## Tests added
| Test | Requirement | Source | Kills |
|---|---|---|---|

## Survivors left
<grouped by reason: needs a requirement (with the question), declined, equivalent, unobservable, reverted, not run>

## Weak tests seen
<the table from the plan, with "fix with /deslop --families TEST">

## Limits
<budget and mutants not run · tool or manual · covering tests found by coverage or by reading · parallel on or off and why · anything that couldn't be run>

Work files: <work path> (mutants, results, plan, ledger, bugs, backups)
```

Lead with what the user most needs: whether a bug turned up, then whether the tests got stronger, then what is waiting on them. The per-file table is for reference.
