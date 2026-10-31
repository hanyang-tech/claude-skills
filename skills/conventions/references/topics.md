# Topics

Part 1 lists the fifteen topics: what to ask of the sample and how to count across the scope. Part 2 is how to count well. Each part ends with the shape of the file it feeds.

The searches below are starting points written for ripgrep. Adjust them to the languages in scope, and read the hits: a search finds candidates, and reading confirms them.

## Part 1 — The topics

### T1 Layout and modules
- Where does each kind of code live: by feature (`orders/handler, orders/service`) or by layer (`handlers/orders, services/orders`)?
- What goes in one file: one class, one feature, one concept?
- How are files named? What do index or `__init__` files contain?
- Which imports between areas does the code avoid? Look for layering: handlers never import repositories, `domain` imports nothing from `infra`.
- **Count:** files per placement style. Imports that cross each candidate boundary (`rg -l "from (app\.)?infra" domain/`).

### T2 Naming
- Case style per kind: files, types, functions, constants, test names.
- Words the codebase prefers or avoids: `get` / `fetch` / `load`, `Service` / `Manager`, `id` / `Id` / `ID`, plurals for collections.
- Boolean names (`is_`, `has_`), and the domain vocabulary: the word used for each core concept.
- **Count:** each competing verb or suffix (`rg -o "def (get|fetch|load)_\w+" | cut -d_ -f1 | sort | uniq -c`).

### T3 Errors
- Exceptions or results or error returns?
- Custom error types, and their hierarchy.
- Where errors are caught: locally, or at a boundary handler?
- Wrapping with a cause (`raise … from`, `%w`, `{ cause }`).
- What is returned to the caller or user on failure, and the message style.
- **Count:** raises of custom vs. built-in types. Catch sites and what they do. Wrapping vs. bare re-raise.

### T4 Validation and trust
- Where is input validated: at the edge (schemas, request models, parsers) or in each layer?
- What library does it?
- Which layers assume input is valid?
- How are untrusted values (user input, external APIs) told apart from trusted ones?
- **Count:** validation calls per layer. Endpoints with and without a schema.

### T5 Types and nullability
- How strict is typing: annotations on everything, public only, none?
- `Optional` / `null` handling: early return, defaults, `assert`?
- Data shapes: dataclasses, pydantic, TypedDict, interfaces, classes, records, plain dicts?
- Enums vs. string constants.
- Money, time and IDs: their types, units and time zones.
- **Count:** each data-shape construct. Annotated vs. unannotated public functions (or the type-checker's strictness setting).

### T6 Logging and observability
- Which logger, created how (`logging.getLogger(__name__)`, an injected logger)?
- Structured fields or format strings?
- What each level is used for.
- What's always logged (request IDs, user IDs) and what never is (tokens, personal data).
- Metrics and tracing: which library, and naming.
- What middleware already logs.
- **Count:** logger creation styles. Calls per level. Structured vs. interpolated messages.

### T7 Config and secrets
- How config is loaded: env vars, a settings object, files?
- Where it is read: once at start-up or anywhere?
- Defaults, how secrets are provided, and how feature flags work.
- **Count:** direct `os.environ` / `process.env` reads outside the config module vs. through it.

### T8 Data access
- ORM or query builder or raw SQL?
- Repositories or data-access modules?
- Transactions: where they open and who owns them.
- Migrations: the tool and naming.
- How N+1 queries are avoided.
- **Count:** query sites per layer. Transaction-opening sites.

### T9 Boundaries: handlers, CLIs, jobs, UI
- The shape of a handler: parse → call → map, or more?
- How responses and errors map to status codes or exit codes.
- Auth checks: decorator, middleware or inline?
- UI components: structure, state management, data fetching, styling.
- **Count:** handlers that call the data layer directly vs. through a service. Auth styles.

### T10 Concurrency and async
- Async or sync, and where the line is.
- Background jobs: the library and idempotency.
- Locks, retries and timeouts: which helper is used.
- Cancellation.
- **Count:** retry and timeout implementations (hand-rolled vs. the shared helper).

### T11 Dependencies and construction
- How objects get their dependencies: constructor injection, module-level singletons, a container, globals?
- Factories.
- How tests swap dependencies.
- **Count:** constructor-injected vs. imported-and-called collaborators in the service layer.

### T12 Comments and docs
- Comment density in established files, per hundred lines.
- Do comments say why, or what?
- Docstrings: on every function, public only, rarely? Their format.
- TODO format (with an owner or ticket?).
- READMEs per package.
- **Count:** comment lines per hundred code lines in the sample. Public functions with and without docstrings.

### T13 Tests
- Framework, layout (beside the code or in `tests/`), and file and test naming.
- Fixtures and factories.
- What is mocked and what is real: the database, HTTP, time.
- Parametrization.
- Assertion style.
- Unit vs. integration split, and markers.
- How time and randomness are controlled.
- **Count:** each mocking style. Parametrized vs. copied cases. Tests per test file.

### T14 Library choices and the reuse index
- For each common job, which dependency or in-house helper does it: HTTP, dates and time zones, money, IDs, paths, retries, caching, serialization, validation, collections, string formatting, test data.
- Which helpers everyone imports (from Step 2's import count).
- Dependencies in the manifest that overlap, where one should be preferred.
- **Count:** imports of each competing library. Uses of each in-house helper.
- **Output:** the reuse index table, not conventions.

### T15 Git and change style
- Commit message format (conventional commits? an imperative subject? ticket IDs?), from `git log --format=%s -200`.
- Branch naming, from `git branch -r`.
- PR size and template, from `.github/`.
- Changelog practice.
- **Count:** subjects matching each format.

**Output contract for `3-candidates.md`** (or `3-candidates-<group>.md`):

```
## T3 Errors
- C-T3-1 <candidate, phrased as a rule> — e.g. <path:line>, <path:line>, <path:line>
- C-T3-2 …
- Not this?: <any example seen that breaks a candidate, path:line>
- Written rule?: <the rule from CLAUDE.md / CONTRIBUTING / config that covers this topic, or none>

## T12 Comments and docs
- nothing distinctive: <what was checked>
```

Every topic T1–T15 has a section.

## Part 2 — Counting

**Pick the right denominator.** "Custom errors in 34 of 39 modules that raise" means something. "Custom errors in 34 of 400 files" doesn't. Find the sites where the choice was made first, then count which way each went.

**Count with something you can show.**
1. `rg -c` or `rg -l | wc -l` for textual patterns. Exclude tests, generated and vendored code unless the topic is tests.
2. The linter or type-checker with a rule turned on temporarily, run on a copy of the config in `<work>` and passed with the tool's config flag. Never edit the repo's config.
3. An AST query (`ast-grep`, `semgrep`) if installed, for structural patterns.
4. **Sampled reading** when none of these can tell the cases apart. Pick at least 15 sites at random (`rg -l … | shuf -n 15`), read each, and count. Say it was sampled.

**Strength.**
- **Established:** 80% or more of the applicable sites.
- **Prevailing:** 60–80%.
- **Mixed:** under 60%, or two styles each above 30%.
- Areas can differ. If `apps/web` does one thing and `apps/api` another, record a convention per area, not a mixed one.

**Direction.** Count the same thing in files added in the last 90 days (from Step 2), compared with established files. If the newer files go the other way at 70% or more while the established ones hold the old style, it's a **migration**. If the history is weak, skip direction and say so.

**Exemplars.**
- **The exemplar:** the clearest, shortest place that shows the convention done right, given as `path:line`.
- **The counter-example:** a real place that breaks it, if any.
- Prefer exemplars in established files.

**Output contract for `4-measured.md`:**

```
| ID | Convention | Applies to (denominator) | Holds | % | Strength | Count by | New code | Exemplar | Counter-example |
|---|---|---|---|---|---|---|---|---|---|
| C-T3-1 | Raise subclasses of AppError, not built-ins | modules that raise (39) | 34 | 87 | established | `rg -l "raise \w+Error" src/ ...` | 9/9 | src/orders/service.py:58 | src/legacy/import.py:120 |
| C-T5-2 | Request bodies are pydantic models | handlers with a body (22) | 12 | 55 | mixed (10 dataclass) | sampled 22/22 | 6/7 pydantic | api/orders.py:14 | api/reports.py:30 |

DROPPED: <ID: language default | formatter enforces | duplicate of ID>
MIGRATIONS: <ID: old → new, established files n%, new files n%>
WRITTEN RULES: <rule (source) → followed n/m | ignored>
SKEPTICS: <ID → counter-examples found, count adjusted to …, or "inline, none run">
```
