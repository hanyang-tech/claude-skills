# Formats

This file has the work-file formats for Steps 1 and 2, the doc template, the CLAUDE.md pointer, and how to propose lint rules.

## Work files

**`1-scope.md`**

```
Repository: <path> · scope: <whole | dir>
Languages: <language: n files, …>
Areas: <top-level areas and what each is>
Written rules: <file: what it covers, one line each, or none>
Existing doc: <path, or none> · mode: new | update
Tools: formatter <cmd> · linter <cmd> · types <cmd> · tests <cmd> · boundaries <tool or none>
Doc goes to: <path> · CLAUDE.md: <exists at path | none>
Mode: inline | agents
```

**`2-sample.md`**

```
History: <n> authors · <n> of <n> files recent · reliable | WEAK (counts and the user decide)
| Area | Kind | File | Why chosen (authors / commits / age, or coverage) |
|---|---|---|---|
Shared helpers (by import count): <module: n importers, …>
Recent files for direction: <n> (from established.py)
```

## The doc

Write the doc in this shape. Leave out a section only when it would be empty. Use the codebase's own words and real paths.

```markdown
# Conventions

How code in this repository is written, measured from the code on <date>.
Each convention says how widely it holds:
- **established** (80%+) is what to do.
- **prevailing** (60–80%) is the default, with exceptions the code shows.
- **rule** means the team decided it.

Mixed areas are listed at the end; don't add a third style. Where this doc and `docs/patterns.md` disagree, the patterns file wins.

## Before you push
- Format: `<cmd>` · Lint: `<cmd>` · Types: `<cmd>` · Tests: `<cmd>`
- <anything CI checks that isn't in those, e.g. import boundaries>

## Layout
### CONV-1 Code is grouped by feature (established, 41/45 modules)
- Each feature in `src/<feature>/` has `handler.py`, `service.py`, `repository.py`, `models.py`.
- Example: `src/orders/` · Not this: `src/misc/reports.py`

## Errors
### CONV-7 Raise `AppError` subclasses; let them reach the handler (established, 34/39)
- Define the error in the feature's `errors.py`. Catch only to add context, with `raise … from e`. The boundary at `src/api/errors.py:12` maps them to responses and logs them.
- Example: `src/orders/service.py:58` · Not this: `src/legacy/import.py:120`

<… one section per topic that has conventions; each convention is 2–4 lines …>

## Use these, don't rewrite them
| Job | Use | Where |
|---|---|---|
| HTTP calls | `http_client.get_json` (timeouts and retries built in) | `src/common/http.py:20` |
| Dates and time zones | `pendulum`, always UTC inside | `src/common/time.py` |
| Money | `Money` (integer minor units) | `src/common/money.py:8` |

## Mixed: don't add a third style
- **Request models:** pydantic (12 handlers) vs. dataclasses (10). New code: <the user's decision, or "match the file you're in">.

## Changing
- **CONV-12 HTTP client:** `requests` → `httpx`. Established code 85% `requests`, the last 90 days 6/7 `httpx`. New code uses `httpx`. <(decided by the user, date) | (observed; not confirmed)>

## Recommendations
<Optional and clearly separate: things the code doesn't do consistently and that would be worth adopting. Not conventions.>

## Could be enforced by a tool
| Convention | Tool and rule | Existing violations |
|---|---|---|
| CONV-3 no `infra` imports in `domain` | `import-linter` contract | 2 |

## Changes
- <date>: written by /conventions from <n> files sampled, <n> conventions measured.
```

**Convention entries.**
- **Heading:** `### CONV-<n> <the rule, imperative or declarative> (<strength>, <holds>/<applies>)`. A decided rule reads `(rule, decided <date>)`, or `(rule, from CLAUDE.md)` for a written rule the code follows.
- **Body:** one or two lines. Say what to do concretely enough that a reviewer could check it, and add the why only if it isn't obvious.
- **Last line:** `Example:` and `Not this:` with `path` or `path:line`. Leave out `Not this:` when there's no counter-example.
- **IDs** are never reused. A dropped convention's ID stays retired, and the Changes section says so.
- **Area-specific conventions** say the area in the heading: `CONV-9 (apps/web) …`.

Keep the doc to about 250 lines. Spend the lines on conventions a newcomer would get wrong, the reuse index and what's mixed, which are where agents and new people go wrong.

## The CLAUDE.md pointer

Add or update this section in an existing `CLAUDE.md`. Change nothing else in the file:

```markdown
## Conventions

Read `docs/conventions.md` before writing or reviewing code here. It records how this codebase is actually written: the conventions with their exemplars, the helpers to reuse, and the mixed areas where you shouldn't add another style.
```

If `CLAUDE.md` already has conventions written in it, keep them. Check them against the code in Step 4, and cite them in the doc as `(rule, from CLAUDE.md)`.

## Proposing lint rules

For each established or decided convention a tool can check, propose a rule:

| Kind of convention | Tool |
|---|---|
| Import boundaries | `import-linter` (Python), `eslint-plugin-boundaries` / `dependency-cruiser` (JS/TS), `depguard` (Go), ArchUnit (Java) |
| Banned APIs and libraries | ruff `TID251` banned-api, eslint `no-restricted-imports` / `no-restricted-syntax`, `forbidigo` (Go) |
| Naming | ruff `N`, eslint `@typescript-eslint/naming-convention` |
| Error handling | ruff `BLE`, `TRY`, `S110`, eslint `no-empty` with `allowEmptyCatch: false` |
| Logging | ruff `G`, `T20` (print), eslint `no-console` |
| Anything structural | a `semgrep` or `ast-grep` rule kept in the repo |

Count the existing violations of each rule against a temporary copy of the config, kept in `<work>`, so the user knows what turning it on costs. Propose only. Changing the repo's linter config is an offer in the report, not part of this run.
