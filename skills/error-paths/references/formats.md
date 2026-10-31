# Formats

The output contract for every work file, in step order. Part 1 is the target and the map (Steps 1 and 2). Part 2 is the inventory and the matrix (Steps 3 and 4). Part 3 is verification and the user's decisions (Steps 5 and 6). Part 4 is the plan (Step 7). Part 5 is how to apply it and the ledger (Step 8). Part 6 is the report (Step 10).

IDs are stable for the whole run: operations `O-n`, failure points `FP-n`, matrix rows `M-n`, questions `Q-n`, gap items `G-n`, pin tests `P-n`. In agent mode, prefix them with the group (`A-FP-3`) so files merge without clashes.

## Part 1 — Target and map

**`1-target.md`**

```
Target: <operation in words | uncommitted | branch vs <base> | commit | range | PR #<n> | paths>
Operations: <O-1 name — entry point path:line, …>
Scope: <n> files in the call graphs · changed lines: <n, or "not a diff target">
Changes go to: <the working tree | worktree path and branch | nowhere: report only>
May run code: yes | no: <why>
Options: <as given>
```

**`2-map.md`**

```
OPERATIONS
| Op | Entry point | Trigger | Success promises | Callers / consumers |
|---|---|---|---|---|
| O-1 | `api/orders.py:40` create_order | POST /orders | 201 with order; row in orders; OrderCreated event | web checkout, mobile app |

WRITTEN RULES
- docs/conventions.md: <CONV IDs that bear on errors, logging, retries, tests — or "none">
- docs/patterns.md: <PAT IDs — or "none">
- Contracts: <OpenAPI / proto / schema paths and the error responses they define — or "none">
- Other: <CLAUDE.md, CONTRIBUTING, runbooks — one line each>

FAILURE HANDLING IN THIS CODEBASE (from established code)
- Errors: <style; boundary handler path:line; how errors map to statuses or exit codes>
- Timeouts and retries: <shared client or decorator path:line, its defaults>
- Transactions: <how they are opened, path:line; are external calls kept outside?>
- Idempotency: <keys, unique constraints, processed-message tables, or none>
- Concurrency control: <locking, versions, atomic updates, or none>
- Logging: <library; level for each kind of failure; identifiers carried (request id, user id, order id); redaction>
- User-facing errors: <shape; what is hidden>
- Example: <one path:line where the codebase handles a dependency failure well, to copy>

TEST TOOLS
| Need | Available | How it's used here |
|---|---|---|
| HTTP fake | responses 0.25 | tests/conftest.py:30 fixture `mocked_http` |
| Clock | none | — (inject a clock or write a fake) |
(HTTP fake, raise from a dependency, clock, DB in tests, containers, concurrency, files, generated input, log capture)
Related tests: <command> · Where tests for these files live: <path pattern>

BASELINE TESTS
Command: <…> · <n> passed · <n> failed · <n> skipped · <duration>
Already failing: <test ids, or none>
```

## Part 2 — Inventory and matrix

**`3-inventory.md`** (or `3-inventory-<group>.md`)

```
## O-1 create_order
CALL GRAPH
create_order  api/orders.py:40
├── validate (OrderIn model)  api/schemas.py:12            → FP-1 input
├── OrderService.create  orders/service.py:22
│   ├── inventory.reserve  clients/inventory.py:31          → FP-2 http
│   ├── payments.charge  clients/payments.py:18 (@retry 3×) → FP-3 http
│   ├── session.add + commit  orders/service.py:48          → FP-4 db
│   └── publish OrderCreated  events/bus.py:9               → FP-5 queue
└── charge → commit → publish sequence  orders/service.py:22-60 → FP-6 sequence

FAILURE POINTS
| FP | Op | Kind | Where | What it does | Applies | Not applicable (why) |
|---|---|---|---|---|---|---|
| FP-3 | O-1 | http | `clients/payments.py:18` | POST /charges to the payment provider, wrapped in @retry | TIME, CONN, 5XX, 4XX, SHAPE, DUP, SLOW, WRONG | ORDER: one call per request |
| FP-6 | O-1 | sequence | `orders/service.py:22-60` | charge, then insert, then publish | PART, CRASH, DUP | — |

COULDN'T TRACE: <calls whose target couldn't be resolved (dynamic dispatch, plugins), or none>
```

The call graph stops at each failure point. Every leaf is an `FP`, or says why it can't fail ("pure function", "in-memory constant").

**`4-matrix.md`** (or `4-matrix-<group>.md`)

```
| Row | FP | Failure | Current behavior (traced) | Expected behavior | Source | Verdict | Impact | Sev | Change |
|---|---|---|---|---|---|---|---|---|---|
| M-7 | FP-3 | TIME | `requests.post` without `timeout` (`clients/payments.py:18`) waits until the gunicorn worker timeout (30 s, `gunicorn.conf.py:4`) kills the worker; @retry (`common/retry.py:14`) never fires; the client gets 502 from the proxy; no log with the order id | fail within 10 s, 503 to the caller, no order row, warning log with order id | CONV-12; same handling for the inventory client at `clients/inventory.py:20` | gap | RESOURCE, USER | 🟠 | new |
| M-9 | FP-6 | PART | charge succeeds, commit fails (`orders/service.py:48`) → exception → 500; the charge is never refunded; nothing logs the charge id | refund, or an order recorded as `payment_captured` to reconcile | unknown | unknown | STATE | 🔴 | pre-existing |
| M-12 | FP-1 | HOSTILE | pydantic rejects extra fields and wrong types (`api/schemas.py:12`, `extra="forbid"`) → 422 with field errors via FastAPI | 422 naming the field | OpenAPI `/orders` 422 | handled | — | — | pre-existing |

SUMMARY: <n> rows · <n> handled · <n> gap · <n> unknown · by operation: O-1 <h>/<g>/<u>, …
```

- **Current behavior** names every place the failure passes through, with `path:line`, ending in what the caller, the stored state and the logs see.
- **Source** is a document ID (`CONV-12`, `PAT-3`, an OpenAPI path), a requirement, a codebase precedent with `path:line`, a decision (`Q-2`), or `unknown`.
- **Change** is `new` when the changed lines caused or touched the row, `pre-existing` otherwise, and `—` for a target that isn't a diff.
- **Impact** and **Sev** are filled for gaps and unknowns, using Part 3 of the catalog.

## Part 3 — Verification and decisions

**`5-verification.md`**

```
| Row | Claim | Reachable? | Handled upstream? | Checked how | Result | Impact | Sev |
|---|---|---|---|---|---|---|---|
| M-7 | payment call has no timeout | yes: real network call | no: nothing sets a default on the session (`clients/payments.py:6`); the worker kill at 30 s skips every handler | read requests 2.32 `sessions.py` (no default timeout); gunicorn config | Confirmed (worse: the charge may land after the worker dies, with no order row) | RESOURCE, STATE | 🔴 |
| M-15 | duplicate OrderCreated on redelivery | no | yes: consumer upserts on event id (`consumers/orders.py:30`) | read consumer | Dropped: handled upstream | — | — |

MERGED: <M-7, M-16, M-21 → one cause (no client timeout); or none>
SKEPTICS: <row → verdict, or "inline mode, none run">
RE-RATED: <row: old → new severity or impact and why, or none>
```

**`6-decisions.md`**

```
| Q | Rows | Question | Options, recommended first | Answer | Date |
|---|---|---|---|---|---|
| Q-1 | M-9 | If the charge succeeds and saving the order fails, what should happen? | Refund at once and return 503 (the way `subscriptions/service.py:80` handles it) · Save the order as payment_captured for reconciliation · Leave it to the nightly reconciliation | Refund at once | 2026-10-31 |

NOW GAPS: <rows the answers turned into gaps, re-verified in Step 5: yes/no>
NOW HANDLED: <rows, or none>
OPEN: <each unknown row not asked or not answered, with the question it needs>
```

## Part 4 — The plan

**`7-plan.md`**, which is also what the user sees:

```
# Error-paths plan — <target>

Scope: <n> operations · <n> failure points · <n> matrix rows · changes go to <where>
Baseline: tests <pass>/<fail> (<n> already failing)

## Matrix
| Operation | Handled | Gaps | Unknown | 🔴 | 🟠 | 🟡 |
|---|---|---|---|---|---|---|

## Most dangerous first
<the 🔴 gaps and the worst 🟠: ID, the failure in plain words, current → expected, impact>

## Gaps
### G-1 Payment call has no timeout (M-7, M-16, M-21) · 🔴 STATE, RESOURCE
- Test: `tests/orders/test_create_order.py::test_charge_timeout_returns_503_and_saves_no_order` — `responses` registers the charge URL to raise `requests.exceptions.ReadTimeout`; asserts 503, no row in orders, one warning log with the order id
- Fix: pass `timeout=settings.HTTP_TIMEOUT` (`clients/payments.py:18`), as `clients/inventory.py:20` does; map the timeout to `UpstreamUnavailable` (`common/errors.py:44`)
- What changes: callers get 503 within 10 s instead of 502 after 30 s; operators see a warning with the order id
- Fix? yes / no

## Pin tests (optional)
| P | Rows | Test | Why pin it |
|---|---|---|---|
| P-1 | M-12 | `test_create_order_rejects_unknown_fields` | the 422 contract is public |

## Open
<unknown rows with their question, and gaps that need a decision the code can't make (a new dependency, a design choice), each with what it needs>

## Dropped in verification
<n> rows, by reason (unreachable, handled upstream at <path:line>, …)

Needs installing to test: <tool, and the gaps it would cover — or none>

DECISION: <filled in after the user answers: G-1 yes, G-2 no, …; pins P-1, P-3 | with --auto: tests written, fixes asked one by one>
```

Keep each gap to its five lines. The user approves the fixes from this file, so the current and expected behavior have to be clear without opening the matrix.

## Part 5 — Applying

**Before the first edit**
- Confirm the target is in the state Step 3 found: on a branch, the head sha is unchanged; on the working tree, the files in the call graphs haven't changed (`git diff --stat`, or file hashes).
- If anything moved, redo Steps 3 and 4 for the operations that changed before touching them.
- Copy each file to `<work>/backup/<path>` the first time it is touched. Keep a copy before each item in `<work>/backup/G-<n>/`, so an item can be reverted without undoing the ones before it.

**For each gap item, most dangerous first**
1. **Test.** Write it where the codebase keeps tests for that code, with its fixtures and naming. Simulate the failure at the boundary (Part 4 of the catalog). Assert the expected behavior from the matrix: the response, the stored state, what was sent, and the log line.
2. **Prove the gap.** Run the test alone. Record the failure line.
   - Fails on the assertion the gap predicts: the gap is proven.
   - Fails for another reason (import, fixture, setup): fix the test, not the code, and run it again.
   - Passes: the gap was wrong. Mark it `dropped: test passes on current code`, and move the test to the pin tests if the user wanted pins, or delete it.
3. **Fix**, only with a yes for this item. The minimal change the plan row describes:
   - Use the codebase's helpers for timeouts, retries, transactions and errors, from `2-map.md`.
   - Log once, where the codebase logs this kind of failure, at the level its conventions give: usually warning for a handled dependency failure, error for one that fails the operation, info or debug for an expected domain outcome like a 404.
   - Carry the identifiers the conventions name (request id, entity ids, the dependency's name, attempt count, elapsed time). Never a secret, token, password, card number or personal data the codebase doesn't already log.
   - Errors to the user say what happened in the codebase's error shape and hide internals: no stack traces, hostnames, SQL or dependency bodies.
   - No new dependency. A fix that needs one goes back to the user as its own question.
   - Change nothing the plan row doesn't name: no reformatting, no renames, no other gap's fix on the way.
4. **Check.** Run the formatter on the touched files if the project uses one, then the new test (it passes now), the related tests, the linter and the type-checker on the touched files.
5. **Compare with the baseline.**
   - Nothing new fails: `fixed`.
   - Something new fails: restore the item's files from `<work>/backup/G-<n>/`, and mark it `reverted` with the failing test and its error. Keep the gap test in `<work>/held-tests/`.
   - An existing test fails because it asserted the old behavior on purpose (a test that expected the 500): stop and ask. Don't edit it to pass on your own.
   - A test that fails at random: run it up to three times. If it passes now and then, it is flaky, noted and not counted against the item.
6. **No yes for the fix,** or `--auto` with no answer yet: move the gap test to `<work>/held-tests/<path>`, so the suite isn't left red. If the ecosystem has a strict expected-failure marker (pytest `xfail(strict=True)`, jest `test.failing`, vitest `test.fails`, RSpec `pending`), offer it in the report as a way to keep the test in the suite. Status `declined`, or `pending` while waiting.
7. **Record** the item in `8-ledger.md` before starting the next.

**Pin tests,** after the gaps, in batches by test file. Each must pass on the current code. One that fails has found a gap the matrix called handled: mark the row a gap, take the test out, and ask about it.

**After all items**
- Run the full suite once. A new failure here means two items together broke something. Revert items, last first, until it passes, and mark the culprit `reverted`.
- Self-check the diff (SKILL.md, Step 8), and record what was fixed.

**`8-ledger.md`**

```
| Item | Rows | Test | Before fix | Fix | Status | Check |
|---|---|---|---|---|---|---|
| G-1 | M-7, M-16, M-21 | `tests/orders/test_create_order.py::test_charge_timeout_returns_503_and_saves_no_order` | failed: expected 503, got 500 | timeout on client, mapped to UpstreamUnavailable | fixed | test passes · 64 related pass · lint ok |
| G-2 | M-9 | `…::test_commit_failure_refunds_charge` | failed: refund not called | refund in except block | reverted | `test_order_metrics` failed: <error line> |
| G-3 | M-30 | `…::test_duplicate_webhook_charges_once` | passed | — | dropped: test passes on current code | kept as pin |
| G-4 | M-41 | `…::test_stale_event_ignored` | failed as predicted | — | declined | test in held-tests/ |
| P-1 | M-12 | `…::test_create_order_rejects_unknown_fields` | passed | — | pinned | |

FILES TOUCHED: <path → items>
FULL SUITE: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
SELF-CHECK: <what the diff check found and fixed, or nothing>
```

Statuses: `fixed`, `reverted` (with the failure), `declined`, `pending` (waiting for a yes), `deferred` (approved but can't be done safely now, with why), `dropped` (test passed first), `pinned`, `skipped` (with the reason). Every gap item and pin test has exactly one row.

## Part 6 — The report

**`report.md`**

```
# Error paths — <target>

<two or three sentences: what was examined, how many failure modes, what was found and fixed, what is still dangerous, whether the suite passes>

## Still dangerous
<open and declined gaps, 🔴 first: the failure in plain words, what happens today, impact, and what it needs (a decision, a fix approval, a tool)>

## Matrix
| Operation | Rows | Handled | Fixed | Open | Declined | Dropped |
|---|---|---|---|---|---|---|

## Fixed
<each: the failure, what now happens instead, who sees the difference, the test that proves it>

## Tests added
- <n> gap tests, <n> pin tests · <paths>
- Held out of the suite: <n> in <work>/held-tests/ (declined or reverted fixes)

## Reverted
<each: the gap, what broke, and what that suggests>

## Open questions
<each unknown still open: the question, the rows, the recommended answer>

## Result
- Tests: baseline <pass>/<fail> → after <pass>/<fail> · new failures: none | <list>
- Diff: +<n> / −<n> lines across <n> files · <where the changes are>

## Limits
<what couldn't be traced or simulated, failures skipped by --failures, tools missing, code not run and why>

Work files: <work path> (matrix, plan, ledger, held tests, backups)
```

Lead with what is still dangerous and what is waiting on the user. A run that fixed ten 🟡 rows and left one 🔴 open has to say the 🔴 first.
