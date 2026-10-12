# Conventions: learning them, then checking the PR against them

Part 1 finds out how this codebase does things. Part 2 checks the PR against that. The reviewer's own preferences play no part in either: a convention is what the project wrote down or what its code already does.

## Part 1 — Learn the conventions

There are three sources. When they disagree, the higher one wins.

### 1. Written rules

Look for, and read:

- The patterns file: the path given with `--patterns`, else `docs/patterns.md`. Its entries have an ID (`PAT-n`), a strength (`must` or `should`), where they apply, and often an exemplar file. Use the IDs in findings.
- `CLAUDE.md` and `AGENTS.md`, at the root and in the directories the PR touches.
- `CONTRIBUTING.md`, architecture notes, ADRs or RFCs under `docs/`, and a README inside the module being changed.
- The PR template and `CODEOWNERS`, which sometimes carry rules.

Take only the rules that bear on what this PR touches. Note each rule's scope: a rule for the API layer doesn't bind a migration script.

### 2. Tools

Find the formatter, linter, type-checker and test-runner config (`pyproject.toml`, `ruff.toml`, `.eslintrc*`, `biome.json`, `.prettierrc*`, `tsconfig.json`, `.editorconfig`, `Makefile`, the scripts in `package.json`, the CI workflow). They tell you two things:

- **What style is already enforced.** Anything a tool decides is not a review topic.
- **Rules beyond style** that the project chose to enforce: import boundaries, banned calls, required type strictness, naming rules.

### 3. The existing code

This is where most conventions live, unwritten.

**List the kinds of thing the PR adds or changes.** For example: an HTTP handler, a service function, a database query, a model or schema, a migration, a background job, a React component, a hook, a config entry, a unit test, an error type.

**For each kind, find two or three existing examples.** Nearest first: the same directory, then the same module, then the rest of the repository. Prefer examples that are recent (`git log -1 --format=%cs -- <path>`) and that the PR didn't write: files it doesn't touch, or the base version of ones it does. If the patterns file names an exemplar, start there.

**Read each example for:**

| Aspect | What to note |
|---|---|
| Placement | Which directory and file a thing of this kind lives in. One per file, or grouped. |
| Naming | Files, functions, classes, variables, tests, routes, database columns. |
| Layering | Which layer holds which responsibility, and which may call which. What a handler does itself and what it hands on. |
| Data access | Through a repository, a service, an ORM model, a query builder, or raw SQL. How transactions are opened. |
| Errors | Raised or returned. Which error types. Where they are caught and how they become a response. What is logged, and at what level. |
| Validation | Where input is checked, and with what (a schema library, a decorator, by hand). |
| Shared helpers | The utilities everyone uses for this job: the HTTP client wrapper, the auth check, the money type, the date helper, the logger. |
| Types | How much is annotated, and how data crossing a boundary is typed. |
| Config and flags | How a setting or feature flag is read. |
| Tests | Where they live, how they are named, which fixtures and factories they use, what is mocked and what is real, how many cases a typical test file covers. |

**Decide what counts.** A convention is established when:

- it is written down, or
- at least two independent examples do it the same way and you found none that does it another way.

If the examples disagree, it is a **mixed** convention. Record both ways, how many of each you saw, and which is newer. A search often settles the count quickly.

One example is not a convention. Nor is what most projects in this language do, if this project doesn't.

### Conventions list

Every section appears. `KINDS` has a row for each kind of thing the PR adds or changes, and lists the examples you opened, not ones you only found by name.

```
KINDS
| Kind of thing the PR adds or changes | In the PR at | Examples read | Conventions it gave |
|---|---|---|---|
| HTTP handler | <path:line> | <path>, <path>, <path> | V1, V2 |
| Migration | <path> | none: this is the project's first | — |

CONVENTIONS
- [V1] <the rule, stated so that code can be checked against it>
  Source: written: <file, and PAT-n if any> | observed: <path:line>, <path:line> (<count> found, <count> other)
  Strength: must | should | observed | mixed
  Bears on: <which part of the PR>

TOOLS
- Format: <tool and command, or none>   Lint: <…>   Types: <…>   Tests: <…>
- CI on this PR: <passing | failing: which checks | none>
```

Keep it short. Ten entries that bear on the PR are worth more than fifty that describe the codebase.

## Part 2 — Check the PR against them

### 1. Go through what the PR adds

For each new or changed thing, take the conventions that bear on it and compare, aspect by aspect, using the table above. Look hardest at:

- **A helper bypassed.** The PR does by hand what a shared helper does for everyone else. The helper usually does more than is obvious: it validates, logs, retries, checks permissions, or normalizes. Read it and say what the PR's version leaves out.
- **A layer skipped.** A handler that queries the database where others go through a service; a component that fetches where others use the data hook.
- **A second way introduced.** A new error type beside the existing ones, another HTTP client, a different way to read config, a different test layout.
- **A written rule broken.**
- **Tests that don't follow the project's test conventions,** so that they miss its fixtures, aren't collected by the runner, or mock what the project's tests keep real.

### 2. Each departure needs evidence

A departure is a finding only when you can show all three:

- **the PR's way,** at `path:line`
- **the established way,** stated as a rule
- **where it is established:** the written rule, or at least two existing locations, with a count where a search can give one

Without the third it is your preference. Leave it out.

### 3. Say what it costs

- A safeguard that the established way applies and this code skips. Name the safeguard.
- A second way to do the same thing, which the next reader has to learn and the next change has to keep in step.
- A test, route, job or migration that the project's tooling won't pick up because it isn't where or how the tooling expects.
- Nothing beyond inconsistency. Say that too, and rate it **consider**.

If the departure produces a wrong result, it is also an uncovered case. Report it once, as the case, and note the convention in it.

### 4. Not findings

- **A mixed convention.** The PR picked one of two ways already in use. Mention the mix under Questions if it seems worth settling.
- **A deliberate move.** If the PR's way looks like the start of a migration (the description says so, or recent commits moved other code the same way), ask whether the old way is being retired. Don't fault the PR for leading.
- **A better way.** The PR's way may be better than the convention. The inconsistency is still worth one line, as a question: follow the convention here and change it everywhere separately, or confirm the change is intended.
- **Existing code** that breaks a convention. The review covers what the PR changed.
- **Style.** See below.

### 5. Style belongs to the tools

Where running code is allowed, run the project's formatter and linter in check mode on the changed files only. Otherwise read the CI result. Report the outcome in one line, with the failing rule names if it failed.

Don't comment on spacing, quotes, line length, import order or anything else a formatter decides. If the project has no formatter or linter, don't act as one. Report only departures that meet the evidence rule above, such as a file-naming scheme that every other file follows.

### Rating

- **should fix:** breaks a written rule, or skips a safeguard the established way provides
- **consider:** departs from an unwritten convention with no direct consequence

A departure is **must fix** only through the bug it causes, and then it is reported as an uncovered case.

## Output contract

Return the conventions list from Part 1 if you built or extended it, then the sections below. Every section appears; one with nothing to list says `none` and why. Each kind in `KINDS` shows up under `DEPARTURES` or under `FOLLOWS THE CODEBASE`, so that a kind nobody checked can be seen.

```
DEPARTURES
- [D1] <what differs> — path:line
  In this PR: <how it does it>
  In the codebase: <the established way>
  Established by: written: <file, PAT-n> | observed: <path:line>, <path:line> (<count> this way, <count> the PR's way)
  Cost: <what the difference costs, or "inconsistency only">
  Suggested change: <how to bring it in line>
  Severity: should fix | consider
  Confidence: high | medium | low

TOOLS
- Formatter: pass | fail: <summary> | not run: <why>
- Linter: pass | fail: <rules> | not run: <why>

QUESTIONS
- <mixed conventions worth settling, and moves that look deliberate>

FOLLOWS THE CODEBASE
- <kind>: <aspects checked where the PR does it the established way, and the convention each was checked against>
```
