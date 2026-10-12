# Artifact Templates

Create these in the work directory at Step 0. Keep them short; they are working documents that agents read every iteration, so every extra paragraph is paid for many times.

---

## state.md

The ledger. Update it whenever the phase changes, and read it first when resuming.

```markdown
# <work>: state

- **Branch:** `sdlc/<slug>` (base: `<default branch>`)
- **Iteration:** 2 of max 5
- **Phase:** 5 Verify (fix round 1 of 3)
- **Gates:** requirements ✅ approved · design ✅ approved · release ⏳
- **Mode:** interactive | --auto

## Checks
- test: `<command>`
- lint: `<command>`
- format: `<command>` | none
- typecheck: `<command>`
- build: `<command>`
- coverage: `<command>` | none

## Scanners
| Category | Command | Baseline (before this work) |
|---|---|---|
| Dependencies | `<command>` | 2 existing (1 high, 1 low) |
| Secrets | `<command>` | clean |
| Static analysis | none | not checked |

## Roles
| Role | Agent type | Model |
|---|---|---|
| Driver | this session | <session model> |
| Architect | … | opus |
| Engineer | … | sonnet |
| Reviewer | … | opus |
| Tester | … | sonnet |
| Final reviewer | … | opus |
| Security reviewer | … | opus |
| Skeptic | general-purpose | opus |

<overrides from `--models`, escalations and substitutions, each with the iteration and reason>

## Standards
- **Patterns file:** `docs/patterns.md` | none yet (will be created at `docs/patterns.md`)
- **Languages:**

| Language | Reference (absolute path) | Formatter | Linter |
|---|---|---|---|
| Python | `<skill dir>/references/languages/python.md` | `ruff format` | `ruff check` |
| SQL | none: agents name the standard they apply | none | none |

| Pattern | Strength | Exemplar | Check | Status |
|---|---|---|---|---|
| PAT-1 | must | `api/orders/handler.py` | `lint-imports` | confirmed |
| PAT-2 | must | `billing/money.py` (provisional, it. 2) | review only | exemplar awaiting confirmation |
| PAT-3 | should (proposed) | none yet | review only | inferred under --auto |

## Acceptance criteria and invariants
| ID | Status | Verified by | Iteration |
|---|---|---|---|
| AC-1 | ✅ verified | `tests/…::test_name` | 1 |
| AC-2 | 🔨 in progress | — | 2 |
| AC-3 [security] | ⬜ open | — | — |
| INV-1 | ✅ verified | `tests/…::test_name` | 1 |
| INV-2 | ➖ untouched: <reason> | — | — |

## Log
- Iteration 1: <slice> → AC-1 verified, 1 fix round. Commit `<sha>`.
- Iteration 2: <slice> → …
```

---

## requirements.md

```markdown
# <work>: requirements

## Goal
<the problem being solved and for whom, in two or three sentences>

## Non-goals
- <what this work deliberately leaves out>

## Acceptance criteria
- **AC-1** <concrete input or state → observable outcome>
- **AC-2** … *(assumed)*
- **AC-3 [security]** <abuse case from the threat model → how it is refused>

## Invariants
- **INV-1** <existing behavior or rule that must not break, written as concretely as a criterion>

## Sources
<spec path, ticket, the user's answers; note anything that couldn't be opened>

## Changes
- <date>, iteration <n>: <what changed and what prompted it>
```

Mark a criterion `(assumed)` when the user hasn't confirmed it. `[security]` criteria come from the threat model in `design.md`. Never renumber criteria or invariants; retire one by striking it through with the reason, so earlier iteration files still make sense.

---

## design.md

Written by the architect. The sections are listed in the architect brief in [roles.md](roles.md): Approach, Components and files, Contracts, Data model, Decisions, Risks, Patterns, Threat model, Criteria coverage. A pattern exception the user granted goes under Decisions with its reason. When no design is needed and no trust boundary is crossed:

```markdown
# <work>: design

No separate design needed: <reason, e.g. "single-file change following the existing handler pattern in `api/orders.py`">.

No new attack surface: <reason, e.g. "no new input, endpoint, permission, secret, or stored data">.
```

---

## Patterns file

Lives in the project, not the work directory (default `docs/patterns.md`). Create it when the first pattern is captured. It holds only what the user confirmed.

```markdown
# Implementation patterns

How code in this project is built. `must` patterns are rules; `should` patterns are defaults that a slice may leave with a stated reason. IDs are never reused.

### PAT-1 Handlers don't touch the database (must)
- **Rule:** an HTTP handler parses the request, calls one service function, and maps the result to a response. Only repository classes run queries.
- **Applies to:** everything under `api/`
- **Why:** queries in handlers can't be reused or tested without HTTP.
- **Exemplar:** `api/orders/handler.py`, `orders/repository.py`
- **Not this:** `api/legacy/reports.py` (query built inside the handler)
- **Check:** `lint-imports` contract `api-no-db` | review only

### PAT-2 Money is an integer of minor units (must)
- **Rule:** amounts are `int` cents with a currency code beside them; convert to a decimal string only at the display or API edge.
- **Applies to:** all code
- **Why:** float rounding.
- **Exemplar:** none yet (provisional: `billing/money.py`, iteration 2)
- **Check:** review only

## Changes
- <date>: PAT-2 added, from the user's correction in iteration 1 of <work>.
```

A good rule can be checked by someone who has never spoken to the user. **Applies to** keeps a pattern from being forced onto code it was never meant for. **Not this** is optional and worth adding when there is a tempting wrong way already in the codebase. Mark a pattern `(proposed)` after its strength if the user hasn't confirmed it. Retire a pattern by striking it through with the reason.

---

## backlog.md

```markdown
# <work>: backlog

Ordered. The top item is the next iteration's slice.

| # | Slice | Criteria | Kind | Status | Notes |
|---|---|---|---|---|---|
| 1 | <vertical slice> | AC-1 | slice | ✅ done (it. 1) | |
| 2 | <vertical slice> | AC-2, AC-3 | slice | 🔨 it. 2 | |
| 3 | <bug found by tester in it. 1> | AC-1 | bug | ⬜ must | |
| 4 | <deferred MINOR finding> | — | follow-up | ⬜ optional | from review, it. 1 |
```

**Kind** is `slice`, `bug`, `follow-up`, or `feedback` (CI failures and PR comments after release). **Status** is `must` or `optional` until an item is picked up; only `must` items block release.

---

## iterations/NN.md

One file per iteration. Fill each section as its phase finishes, and tick the phase only when its section, and any agent report it depends on, is on disk. The agents' reports go beside it in `iterations/<NN>/`.

```markdown
# Iteration <n>: <slice>

## Phases
- [x] 1 Requirements: no change
- [x] 2 Design: no change
- [x] 3 Plan
- [ ] 4 Build
- [ ] 5 Verify
- [ ] 6 Integrate
- [ ] 7 Retro

## Requirements and design
<"no change", or what was revisited and why>

## Plan
- **Slice:** <what will work at the end of this iteration>
- **Criteria:** AC-2, AC-3
- **Invariants it could affect:** INV-1 (no test yet)
- **Patterns:** PAT-1 (exemplar `api/orders/handler.py`), PAT-2 (no exemplar yet; this slice creates it)
- **Files likely touched:** <paths>
- **Done means:** <the observable result>

## Build
- **Report:** `iterations/<NN>/engineer-r1.md`
- **Changed files:** <paths>
- **Checks:** <each command and its result, from the report>
- **Patterns:** <the engineer's line per PAT-n>
- **Blocked:** none | <what can't be built as designed>

## Verify
| Round | Reviewer | Tester | Sent back to engineer |
|---|---|---|---|
| 1 | CHANGES_REQUESTED (1 blocker, 2 major) | FAIL (AC-3) | #1–#4 |
| 2 | APPROVED | PASS | — |

<disputed items and how each was resolved>

- **Reports:** `iterations/<NN>/reviewer-r1.md`, `tester-r1.md`, `engineer-r2.md`, `reviewer-r2.md`, `tester-r2.md`
- **Patterns:** <the reviewer's result per PAT-n>
- **Edge cases from the implementation:** <cases tested; branches in changed code left untested and why>
- **Unspecified cases:** <each case, how it was settled, and the criterion or invariant it became>

## Integrate
- Checks: <each command and its result>
- Scanners: <each tool: new findings against the baseline, or "none">
- Exemplars: <new exemplar file and whether the user confirmed it, or "none">
- Completeness, counted from the reports before committing:

| What | Expected | Done | Gap and reason |
|---|---|---|---|
| Phase sections written | 7 | 7 | |
| Agent reports on disk, against agents launched | 6 | 6 | |
| Reports sent back for a missing contract section | — | 1 | tester r1 had no COVERAGE |
| Criteria in the slice with a passing test | 2 | 2 | |
| Invariants the plan names with a passing test | 1 | 1 | |
| Patterns in the plan with an engineer line and a reviewer row | 2 | 2 | |
| BLOCKER and MAJOR findings closed | 3 | 3 | |
| Cases the reviewer walked · listed as untested · now tested | 31 · 4 | 3 | U2 needs a real bucket; backlog #6 |
| Unspecified cases settled | 1 | 0 | asked the user, answer pending |
| Uncovered branches in changed code tested or explained | 5 | 5 | or "no coverage tool" |
| Checks run by the driver and passing | 5 | 5 | |
| Scanner categories run | 3 | 2 | static analysis: no tool |

- Commit: `<sha>` <message>

## Retro
- **Delivered:** <criteria verified>
- **Learned:** <what changes the plan>
- **Queued:** <new backlog items; pattern candidates; anything for next iteration's Requirements or Design>
- **DECISION:** CONTINUE | RELEASE | ASK: <reason>
```

The Build section leaves out the engineer's account of how the code works. The reviewer and tester read this file, and they are meant to judge the code without the author's story about it.

In the completeness table, a criterion, an invariant, a `must` pattern, a BLOCKER or MAJOR finding, a check, a phase section or a report that falls short of "expected" stops the commit. The other rows may fall short with a reason and a backlog or open item. The numbers above are examples.

---

## release.md

Doubles as the PR description.

```markdown
# <work>

## What changed
<two or three sentences a reviewer can read cold>

## Acceptance criteria
| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | … | `tests/…::test_name` |

## Security
- **Threat model:** <each abuse case, the criterion covering it, and its test; or "no new attack surface: <reason>">
- **Scanners:** <each tool and its result against the baseline; categories with no tool>
- **Security pass:** <result, and any finding the skeptic refuted>

## Design notes
<decisions a reviewer should know about, especially anything hard to reverse, and any pattern exception with its reason>

## How to test
<commands, and any manual check for criteria that couldn't be automated>

## Known limits and follow-ups
<optional backlog items left open, assumptions that were never confirmed>
```
