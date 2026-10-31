# Artifact Templates

Create these in the work directory at Step 0. Keep them short; they are working documents that agents read every iteration, so every extra paragraph is paid for many times.

---

## state.md

The ledger. Update it whenever a lane's phase changes, and read it first when resuming.

```markdown
# <work>: state

- **Branch:** `sdlc/<slug>` (base: `<default branch>`)
- **Iteration:** 2 of max 5
- **Lanes:** 2a 5 Verify (delta round 1 of 3) · 2b 6 Integrate · 2c 4 Build
- **Gates:** requirements ✅ approved · design ✅ approved · release ⏳
- **Mode:** interactive | --auto · verify: auto | full | light

## Checks
- test (full suite): `<command>` · about <n> min
- test (targeted): `<command with a path, package or files placeholder>`
- lint: `<command>`
- format: `<command>` | none
- typecheck: `<command>`
- build: `<command>`
- coverage: `<command>` | none

## Lanes setup
- **Parallel-safe:** yes | no: <reason, e.g. "tests bind port 5432 on a shared local database">
- **Max lanes:** 3
- **Worktree root:** `<repo parent>/<repo name>.worktrees/`
- **Worktree setup:** `<command, e.g. npm ci>` | none

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
| Verifier | general-purpose | sonnet |
| Final reviewer | … | opus |
| Security reviewer | … | opus |
| Skeptic | general-purpose | opus |

<overrides from `--models`, escalations and substitutions, each with the iteration, lane and reason>

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
| PAT-2 | must | `billing/money.py` (provisional, it. 2a) | review only | exemplar awaiting confirmation |
| PAT-3 | should (proposed) | none yet | review only | inferred under --auto |

## Acceptance criteria and invariants
| ID | Status | Verified by | Iteration |
|---|---|---|---|
| AC-1 | ✅ verified | `tests/…::test_name` | 1a |
| AC-2 | 🔨 in progress | — | 2b |
| AC-3 [security] | ⬜ open | — | — |
| AC-4 | ⚠️ unverified: flaky test, backlog #7 | — | 2a |
| INV-1 | ✅ verified | `tests/…::test_name` | 1a |
| INV-2 | ➖ untouched: <reason> | — | — |

## Log
- <time> Setup done. Full suite: 6 min.
- Iteration 1 (<wall-clock>): a <slice> → AC-1 verified, full verify, 1 fix round · b <slice> → AC-5 verified, light verify, 0 fix rounds. Full suite 1×. Commits `<sha>`, `<sha>`.
- Iteration 2: …
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

Written by the architect. The sections are listed in the architect brief in [roles.md](roles.md): Approach, Components and files, Dependencies, Contracts, Data model, Decisions, Risks, Patterns, Threat model, Criteria coverage. A pattern exception the user granted goes under Decisions with its reason. A design change the driver makes itself (one that touches no contract, data model, trust boundary or dependency) is a dated line under Decisions:

```markdown
- <date>, it. 2b (driver): <what changed> — prompted by <finding or report>. No contract, data model, trust boundary or dependency affected.
```

When no design is needed and no trust boundary is crossed:

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
- **Exemplar:** none yet (provisional: `billing/money.py`, iteration 2a)
- **Check:** review only

## Changes
- <date>: PAT-2 added, from the user's correction in iteration 1 of <work>.
```

A good rule can be checked by someone who has never spoken to the user. **Applies to** keeps a pattern from being forced onto code it was never meant for. **Not this** is optional and worth adding when there is a tempting wrong way already in the codebase. Mark a pattern `(proposed)` after its strength if the user hasn't confirmed it. Retire a pattern by striking it through with the reason.

---

## backlog.md

```markdown
# <work>: backlog

Ordered by priority. Plan takes lanes from the top, skipping an item that isn't independent of one already chosen.

| # | Slice | Criteria | Depends on | Likely files | Kind | Status | Notes |
|---|---|---|---|---|---|---|---|
| 1 | <vertical slice> | AC-1 | — | `orders/…` | slice | ✅ done (it. 1a) | |
| 2 | <vertical slice> | AC-2, AC-3 | 1 | `orders/export/…` | slice | 🔨 it. 2a | |
| 3 | <vertical slice> | AC-5 | — | `auth/…` | slice | 🔨 it. 2b | |
| 4 | <bug found by tester in it. 1a> | AC-1 | — | | bug | ⬜ must | |
| 5 | <deferred MINOR finding> | — | — | | follow-up | ⬜ optional | reviewer-r1 #4, it. 1a |
| 6 | `tests/test_sync.py::test_retry` | — | — | | flaky | ⬜ optional | 14/20 passes; not touched by this work; it. 2b tester-r1 |
```

**Kind** is `slice`, `bug`, `follow-up`, `flaky`, or `feedback` (CI failures and PR comments after release). **Status** is `must` or `optional` until an item is picked up; only `must` items block release. A flaky test this work added or touched is `must`; one it found but didn't cause is `optional`. A MINOR finding is always `optional`.

---

## iterations/NN.md

One file per iteration: what runs across its lanes. Fill each section as its phase finishes.

```markdown
# Iteration <n>

## Phases
- [x] 1 Requirements: no change
- [x] 2 Design: no change
- [x] 3 Plan
- [ ] 4–5 Build and verify: per lane, see the lane files
- [ ] 6 Integrate
- [ ] 7 Retro

## Requirements and design
<"no change", or what was revisited and why; driver design notes made this iteration>

## Lanes
| Lane | Slice (backlog #) | Criteria | Verify | Working path | Base | Status |
|---|---|---|---|---|---|---|
| a | <slice> (#2) | AC-2, AC-3 | full: `[security]` criterion | `<worktree root>/<slug>-02a` | `<sha>` | merged `<sha>` |
| b | <slice> (#3) | AC-5 | light | `<worktree root>/<slug>-02b` | `<sha>` | merged `<sha>` |

**Why these are independent:** <one line per pair: no shared files except the route table, no dependency>

## Integrate
- Merge order: a, b. Conflicts: <none | route table, resolved by hand>
- **Full suite** on `<sha>`: <pass | n failures>, <duration>
- Failures traced to a lane and fixed: <none | test → lane → fix, rerun result>
- Second full-suite run: <not needed | result on `<sha>`>
- Flaky tests rerun: <none | test (backlog #n) → passed on rerun>
- Worktrees removed: a, b
- Exemplars: <new exemplar file and whether the user confirmed it, or "none">

## Timing
| Phase | Start | End | Wall-clock | Agent time | Notes |
|---|---|---|---|---|---|
| 1–3 Requirements, design, plan | | | | | user wait <n> min |
| 4–5 Lane a | | | | engineer <n>, reviewer <n>, tester <n> | 1 fix round |
| 4–5 Lane b | | | | engineer <n>, verifier <n> | 0 fix rounds |
| 6 Integrate | | | | — | full suite 1× <n> min |
| 7 Retro | | | | — | |
| **Iteration** | | | | | slowest: <lane or phase, and why> |

## Retro
- **Delivered:** <criteria verified, per lane>
- **Learned:** <what changes the plan; lanes that turned out not to be independent>
- **Time:** <the slowest phase or lane and what to change about it, or "nothing to change">
- **Queued:** <new backlog items; deferred MINORs; flaky tests; pattern candidates; anything for next iteration's Requirements or Design>
- **DECISION:** CONTINUE | RELEASE | ASK: <reason>
```

---

## iterations/NNx.md

One file per lane (`02a.md`, `02b.md`, …). It is what the lane's agents are handed. The agents' reports go beside it in `iterations/<NNx>/`.

```markdown
# Iteration <n>, lane <x>: <slice>

## Phases
- [x] 3 Plan
- [ ] 4 Build
- [ ] 5 Verify
- [ ] 6 Lane checks, completeness, merge

## Plan
- **Slice:** <what will work at the end of this lane>
- **Criteria:** AC-2, AC-3
- **Invariants it could affect:** INV-1 (no test yet)
- **Patterns:** PAT-1 (exemplar `api/orders/handler.py`), PAT-2 (no exemplar yet; this slice creates it)
- **Files likely touched:** <paths>; don't touch: <files another lane in this iteration owns>
- **Done means:** <the observable result>
- **Verify:** full | light: <why it qualifies, or which condition it fails>
- **Working path:** `<path>` · **Base:** `<sha>`

## Build
- **Report:** `iterations/<NNx>/engineer-r1.md` · <duration>
- **Changed files:** <paths>
- **Checks:** <each command and its result, from the report>
- **Patterns:** <the engineer's line per PAT-n>
- **Blocked:** none | <what can't be built as designed>
- **Round commit:** `<sha>`

## Verify
| Round | Kind | Reviewer / verifier | Tester | Sent back to engineer | Round commit |
|---|---|---|---|---|---|
| 1 | full | CHANGES_REQUESTED (1 blocker, 2 major, 3 minor) | FAIL (AC-3) | #1–#4 | `<sha>` |
| 2 | delta | APPROVED | PASS | — | `<sha>` |

<disputed items and how each was resolved>

- **Reports:** `iterations/<NNx>/reviewer-r1.md` · <duration>, `tester-r1.md` · <duration>, `engineer-r2.md`, `reviewer-r2.md`, `tester-r2.md`
- **Patterns:** <the reviewer's result per PAT-n>
- **Tests:** <n> existing reused · <n> new · targeted run <n> tests in <duration>
- **Edge cases from the implementation:** <cases tested; branches in changed code left untested and why>
- **Unspecified cases:** <each case, how it was settled, and the criterion or invariant it became>
- **MINORs to the backlog:** <backlog numbers, or none>
- **Flaky:** <none | test · pass rate · added or touched by this slice · backlog number>

## Lane checks and completeness
- Checks: <each command and its result in the lane's checkout>
- Scanners: <each tool: new findings against the baseline, or "none">
- Completeness, counted from the reports before merging:

| What | Expected | Done | Gap and reason |
|---|---|---|---|
| Phase sections written | 4 | 4 | |
| Agent reports on disk, against agents launched | 6 | 6 | |
| Reports sent back for a missing contract section | — | 1 | tester r1 had no FLAKY |
| Criteria in the slice with a passing test | 2 | 2 | |
| Invariants the plan names with a passing test | 1 | 1 | |
| Patterns in the plan with an engineer line and a reviewer row | 2 | 2 | |
| BLOCKER and MAJOR findings closed | 3 | 3 | |
| MINOR findings copied to the backlog | 3 | 3 | |
| Cases the reviewer walked · listed as untested · now tested | 31 · 4 | 3 | U2 needs a real bucket; backlog #6 |
| Unspecified cases settled | 1 | 0 | asked the user, answer pending |
| Uncovered branches in changed code tested or explained | 5 | 5 | or "no coverage tool" |
| Lane checks passing | 4 | 4 | |
| Scanner categories run | 3 | 2 | static analysis: no tool |

- **Squashed commit:** `<sha>` <message> · cherry-picked to `sdlc/<slug>` as `<sha>`
```

The Build section leaves out the engineer's account of how the code works. The reviewer and tester read this file, and they are meant to judge the code without the author's story about it.

In the completeness table, a criterion, an invariant, a `must` pattern, a BLOCKER or MAJOR finding, a check, a phase section or a report that falls short of "expected" stops the merge. The one exception is a criterion left unverified by a flaky test this slice added, after its one fix round: it has a `must` backlog item and is shown as ⚠️ in `state.md`. The other rows may fall short with a reason and a backlog or open item. The numbers above are examples.

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
- **Follow-ups:** <MINOR findings deferred during the run and from the final review, each with its location>
- **Flaky tests:** <tests quarantined in the backlog, with pass rate, and whether this work touched them>
- **Assumptions:** <made under --auto and never confirmed>
```
