# Formats

This file has the output contract for every work file from Step 2 on: the inventory (Step 2), findings (Step 3), verification (Step 4), the plan (Step 5), the ledger (Step 6) and the report (Step 8). `1-target.md` and `7-coverage.md` are in SKILL.md. The classes (A, R, M, B, N) and severities (🔴 🟠 🟡) are defined at the top of [checks.md](checks.md).

## `2-inventory.md` — Step 2

One block per manifest, then the tools, holds and baseline. Paths are relative to the repository root.

**Output contract**

```
# Inventory — <repo> · scope <whole | dir | package>

## Manifests
| # | Manifest | Ecosystem | Lockfile | Manager (version, from) | Workspace | Direct deps runtime / dev / other |
|---|---|---|---|---|---|---|
| M1 | package.json | JS/TS | pnpm-lock.yaml | pnpm 9.12 (packageManager) | root of 6 | 4 / 21 / 0 |
| M2 | apps/api/pyproject.toml | Python | uv.lock | uv (lockfile; CI uses uv sync) | — | 18 / 9 / 2 extras |
Problems: <two lockfiles, lockfile missing, manager unclear and what the user said, or none>
Private, not sent to public services: <scopes, indexes, GOPRIVATE patterns, or none>

## Direct dependencies
### M1 package.json
| Package | Declared | Resolved | Kind |
|---|---|---|---|
| react | ^18.2.0 | 18.3.1 | runtime |
| @types/node | ^20 | 20.14.2 | dev |
<one table per manifest; kind is runtime, dev, optional, peer, build, extra:<name> or group:<name>>

## Holds
| Package | Manifest | Held at | Where it says so | Reason |
|---|---|---|---|---|
| typescript | M1 | ~5.4 | renovate.json packageRules | "5.5 breaks decorators" |
<or: none>

## Written rules
<docs/conventions.md and docs/patterns.md: library choices, mixed areas, migrations under way, import boundaries, one line each with the ID; or none>

## Tools
| Check | M1 | M2 |
|---|---|---|
| VULN | `pnpm audit --json` 🌐 | `pip-audit` not installed → `osv-scanner` 🌐 |
| UNUSED | `knip` (node_modules/.bin) | `deptry` |
| BOUND | none → import_graph.py | `lint-imports` (2 contracts) |
<every check × every manifest; "not installed → <fallback>" or "not run: <why>">

## Baseline
Commands: install `<cmd>` · build `<cmd>` · types `<cmd>` · lint `<cmd>` · tests `<cmd>`
Run: <now | deferred to Step 6: deps not installed | worktree>
| Command | Result | Already failing |
|---|---|---|
| tests | 412 pass / 3 fail / 5 skip | test_tz_parse, test_export_pdf, test_slow_sync (flaky) |
| types | 2 errors | src/legacy/x.ts:40, :88 |
```

## `3-findings.md` — Step 3

Auditors write `3-findings-<group>.md` in this shape, and you merge them into `3-findings.md` keeping their IDs unique. Two parts: a coverage table showing what was run, then the findings.

**Output contract**

```
# Findings — <repo>

## Checks run
| Manifest | Check | How | Result |
|---|---|---|---|
| M1 | VULN | `pnpm audit --json` → raw/vuln-m1.json | 3 advisories |
| M1 | UNUSED | `knip` → raw/unused-m1.json | 5 candidates |
| M2 | VULN | — | not run: no network |
| M2 | MISPLACED | by search | 0 |
| M3 | BOUND | — | n/a: Go compiler forbids package cycles; no written layering rules |
<every manifest × every check in scope; How is the command and raw file, "by search", "n/a: why" or "—"; Result is a count or "not run: why">

## Findings
### VULN-1 🔴 `lodash` 4.17.20 — prototype pollution (GHSA-xxxx, high)
Where: M1 runtime, direct · path: app → lodash
Evidence: raw/vuln-m1.json · advisory range <4.17.21 · resolved 4.17.20
Reachability: called — src/utils/merge.ts:14 calls `_.merge` with request data
Fix: `pnpm update lodash` → 4.17.21 (within ^4.17.0) · Class A

### UNUSED-2 🟠 `moment` (runtime)
Where: M1
Evidence: knip lists it; `rg -n "moment" --hidden -g '!pnpm-lock.yaml'` finds only package.json
Guards checked: dynamic import, config, scripts and CI, types, peer (none needs it)
Fix: `pnpm remove moment` · Class A

### OVERLAP-1 🟠 HTTP clients: axios (23 files) and node-fetch (4 files)
Where: M1 runtime
Evidence: `rg -l "from 'node-fetch'" src` → 4 files: <paths>
Written rule: none | CONV-<n> says <…>
Fix: move the 4 node-fetch callers to the axios wrapper at src/http.ts:5, then remove node-fetch · Class B

### BOUND-1 🟠 cycle: orders ↔ billing
Where: src/orders/service.py:12 → src/billing/invoice.py:8 → src/orders/models.py
Evidence: raw/bound-py.txt (import_graph.py --collapse dir) · runtime edges
Rule: docs/conventions.md CONV-3 "billing depends on orders, never the reverse"
Fix: move `OrderTotal` to src/orders/models.py and import it from there in billing · Class B
```

Every finding has:
- **ID** `<CODE>-<n>`, a severity and a one-line title naming the package and version, or the modules
- **Where:** the manifest, the kind (runtime, dev…), direct or transitive, and for a transitive package the path to it
- **Evidence:** the raw file or the search, with what it showed. For UNUSED, the guards checked. For VULN, the advisory ID, its severity, its affected range and the resolved version, plus the reachability level and what shows it
- **Fix:** the exact command or change, and its class. For OUTDATED, the current and target versions and whether patch, minor or major

## `4-verification.md` — Step 4

**Output contract**

```
# Verification — <repo>

| ID | Disproved by | Verdict | Skeptic | Outcome |
|---|---|---|---|---|
| UNUSED-2 | rg in configs, scripts, CI, Dockerfile; npm ls moment (no peer) | CONFIRMED | opus: CONFIRMED | kept · A |
| UNUSED-3 | `eslint-plugin-import` named in .eslintrc.cjs:4 | REFUTED | — | dropped: used by config |
| VULN-2 | govulncheck: module required, symbol not called | CONFIRMED (imported) | opus: CONFIRMED | kept · priority lowered |
| UNUSED-5 | used only in docs/build.sh, which CI doesn't run | PLAUSIBLE | opus: PLAUSIBLE | kept as N: not removed |
| OUTDATED-4 + VULN-3 | one package | — | — | merged into VULN-3 |

Dropped: <n> — <by reason: used by config 3, peer 1, binary in CI 2, …>
Merged: <n> · Kept: <n> (A <n> · R <n> · M <n> · B <n> · N <n>)
```

Verdicts: `CONFIRMED`, `PLAUSIBLE` (couldn't disprove or prove it), `REFUTED`. Every finding in `3-findings.md` has one row. A finding the skeptic refuted is dropped, unless you can show where the skeptic was wrong, in the row.

## `5-plan.md` — Step 5

This is what the user sees and approves.

**Output contract**

```
# Dependency plan — <repo> · <scope>

Changes go to: <working tree, which also updates node_modules / .venv | worktree path, branch deps/<date>>
Baseline: tests <pass>/<fail> (<n> already failing) · build <ok> · types <n> · lint <n> | deferred to Step 6
Downloads on approval: the versions below, from <configured registries>

## Vulnerabilities
| Severity | Called | Imported | Runtime-transitive | Dev-only | No fix |
|---|---|---|---|---|---|
| critical | 0 | 1 | 0 | 0 | 0 |
| high | 1 | 0 | 2 | 3 | 0 |

## Findings
| Check | 🔴 | 🟠 | 🟡 | A | R | M | B | N |
|---|---|---|---|---|---|---|---|---|
| VULN | | | | | | | | |
| … |
| **Total** | | | | | | | | |

## Batches
| Batch | Class | Manifest | Findings | Changes | Command |
|---|---|---|---|---|---|
| 1 | A | M1 | VULN-1 | lodash 4.17.20 → 4.17.21 | `pnpm update lodash` |
| 2 | A | M1 | UNUSED-2, UNUSED-4 | remove moment, left-pad | `pnpm remove moment left-pad` |
| 4 | A | M2 | OUTDATED-1…9 | 9 patch and minor: <pkg from → to, …> | `uv lock --upgrade-package …` |
| 6 | M | M1 | OUTDATED-12 | eslint 8.57 → 9.12 with plugins <…> | see below |

## Majors and consolidations (a yes for each)
### Batch 6 — eslint 8.57.0 → 9.12.0 (M)
Notes read: <release notes for 9.0.0 … 9.12.0, URL or file> | not read: <why>, read after install
Breaking changes that touch this repo:
- flat config is the default → .eslintrc.cjs becomes eslint.config.js
- <…>
Code changes: .eslintrc.cjs (rewrite), package.json:12 (lint script)
Codemod: `<command>` — runs only if you approve it | none
Moves with it: @typescript-eslint/* 6 → 8, eslint-plugin-react 7.33 → 7.37
New install scripts: none | <packages>

## Report only (N)
<each: what it is, why it can't be fixed here, the decision it needs>

## Held
<each held package: what would have been done and why it's held>

## Not planned
<--no-major: the majors, each with the work it needs · --audit-only: counts of the checks not run>

## Dropped in verification
<n>, by reason

DECISION: <filled in after the user answers: approved all | approved batches … | declined … | majors: 6 yes, 7 no | --auto: batches 1–4 applied, rest pending>
```

## `6-ledger.md` — Step 6

One row per kept finding, and one row per attempt when a batch is split.

**Output contract**

```
# Ledger — <repo>

| Batch | Finding | Package | From → to | Class | Status | Check |
|---|---|---|---|---|---|---|
| 1 | VULN-1 | lodash | 4.17.20 → 4.17.21 | A | applied | install ok · build ok · 412 pass |
| 4 | OUTDATED-1…9 | 9 packages | <…> | A | split | tests: 2 new failures |
| 4a | OUTDATED-1…5 | 5 packages | <…> | A | applied | 412 pass |
| 4b | OUTDATED-6…9 | 4 packages | <…> | A | split | test_dates failed |
| 4b2 | OUTDATED-8 | pendulum | 3.0.0 → 3.1.0 | A | reverted | test_dates: AssertionError <first line> |
| 6 | OUTDATED-12 | eslint | 8.57.0 → 9.12.0 | M | declined | — |
| — | UNUSED-5 | build-tool | — | N | report only | — |
| — | OUTDATED-14 | typescript | 5.4.5 → 5.6.3 | A | held | renovate.json: decorators |

BACKUPS: <batch → files backed up>
LOCKFILES: <file → sync check result after the last batch>
FULL SUITE: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
VULNERABILITIES AFTER: <critical/high/moderate/low> · <command>
```

Statuses:
- **applied**
- **reverted:** with the failing command and its first error line.
- **declined:** the user said no.
- **deferred:** approved, but not done in this run. Say why: `--no-major`, the files changed since Step 3, a dependency on a reverted batch.
- **held:** someone held it back on purpose. Say where.
- **report only**
- **split:** a batch row that was halved. It isn't a final status; its findings each end in one of the others.

Every kept finding has exactly one final status.

## `report.md` — Step 8

**Output contract**

```
# Dependency report — <repo> · <scope>

<two or three sentences: what was checked, what changed, whether the build and tests still pass, and what's waiting on the user>

## Result
- Changes: <working tree | worktree path, branch> · <n> manifests, <n> lockfiles changed
- Vulnerabilities: critical <n> → <n> · high <n> → <n> · moderate <n> → <n> · low <n> → <n>
- Tests: baseline <pass>/<fail> → after <pass>/<fail> · new failures: none | <list>
- Build, types, lint: <before → after>

## Changed
| Package | Manifest | Change | From → to | Why |
|---|---|---|---|---|
| lodash | M1 | updated | 4.17.20 → 4.17.21 | VULN-1 |
| moment | M1 | removed | 2.29.4 → — | UNUSED-2 |
| pytest | M2 | moved to dev | — | MISPLACED-1 |
| zod | apps/web | declared | → ^3.23.8 (already resolved) | MISSING-1 |

## Reverted
<each: the change, what failed, and what it suggests>

## Pending majors and consolidations
| Package | From → to | Work it needs | Notes |
|---|---|---|---|
| eslint | 8.57 → 9.12 | flat config rewrite, 2 plugin majors | <link or path in work dir> |

## Internal boundaries
<cycles and layering violations: the modules, the edges by path:line, the rule they break, the suggested fix; or "none found" with what was run>

## Needs your decision
<N findings, held packages worth revisiting, abandoned or deprecated packages with no drop-in replacement, worst first>

## Limits
<checks not run and why, private packages not checked, ecosystems without a tool, the baseline's existing failures>

Work files: <work path> (inventory, plan, ledger, backups, raw tool output)
```

Lead with what the user most needs: whether vulnerabilities went down, whether the build and tests still pass, and what's waiting on them. The table of changes is for reference and for commit messages.
