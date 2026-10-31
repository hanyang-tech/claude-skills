# Diagnosis

Part 1 is for reading the ranking (Step 2). Part 2 is the cost signals each chosen file is checked for (Step 3). Part 3 is how each finding is disproved (Step 4). Part 4 is the refactoring catalog that steps are taken from (Steps 3 and 4). Part 5 is coverage and characterization tests (Steps 3 and 6). The output contracts for every work file are in [formats.md](formats.md).

## Contents

- Part 1 — Reading the ranking
- Part 2 — Cost signals: LONG, RESP, NEST, DUP, COUP, STATE, NAME, MIX, TYPE
- Part 3 — Verifying findings
- Part 4 — The refactoring catalog
- Part 5 — The safety net

---

## Part 1 — Reading the ranking

**The columns.** `commits` is churn in the window. `bugfix` counts commits whose subject matches `fix|bug|hotfix|revert|regression`. `churned` is lines added plus deleted. `lines` is non-blank, non-comment lines. `indent` is the sum of indentation depth over those lines, a whitespace-complexity proxy that tracks cyclomatic complexity well within one language. `funcs`, `max_func` and `max_nest` come from lines that look like a function's first line: their count, the longest such block, and the deepest nesting inside one. They are approximate. Read the file before quoting them.

**The score** is `churn^w × indent × (1 + bugfix)`, each divided by the largest in scope, with `w = 1`, or `0.5` for a young history. A file needs both churn and complexity to rank high. Bug fixes can at most double the score.

**Reading it.**
- **High on both, with bug fixes:** the classic hotspot. Rank it first.
- **High churn, low complexity:** a registry, a config table, a list of routes. It changes often because it's the place to add things, and that is cheap. Note it and move on, unless it also collects bug fixes.
- **High complexity, no churn:** stable legacy. It costs little until someone has to change it. Mention it, don't pick it.
- **`indent` across languages.** Two-space and four-space code, and languages with namespace and class nesting such as C# and Java, give different baselines. Compare files within one language. JSX markup nesting counts as nesting.
- **Coupling.** A pair with a high share in different modules means one change has to be made in two places. That's a cost of both files and a hint that something lives in the wrong one. A pair of a file and its own test, or of an interface and its one implementation, is expected.
- **Young history.** Under 90 days or 50 commits, most churn is the first build-out. Choose on `indent`, `max_func`, `max_nest` and `bugfix`, and say so.

**Real complexity tools.** When one is installed for the main language, run it on the top files and prefer its numbers. Use the same tool in Step 8. Never install one.

| Ecosystem | Tool | Command |
|---|---|---|
| Python | radon | `radon cc -s -j <files>` (per function), `radon mi -s <files>` |
| Python | ruff | `ruff check --select C901 --config 'lint.mccabe.max-complexity = 0' <files>` (every function with its complexity) |
| Many languages | lizard | `lizard -l <lang> --csv <files>` (CCN, length, parameters per function) |
| JS / TS | eslint | `npx eslint --rule '{"complexity":["warn",0]}' --rule '{"max-depth":["warn",0]}' <files>`, with the project's own config so TS parses |
| Go | gocyclo / gocognit | `gocyclo -over 0 <files>`, `gocognit -over 0 <files>` |
| Rust | clippy | `cargo clippy -- -W clippy::cognitive_complexity` (reports only above the threshold) |
| Java / Kotlin | PMD, detekt | `pmd check -R category/java/design.xml/CyclomaticComplexity -d <files>`, `detekt --input <files>` |
| Ruby | rubocop | `rubocop --only Metrics/CyclomaticComplexity,Metrics/MethodLength,Metrics/AbcSize <files>` |
| C# | lizard, or Roslyn metrics | `lizard -l csharp <files>` |

---

## Part 2 — Cost signals

Go through every signal for every chosen file. For each, **Looks like** says what to hunt, **Evidence** says what to record, **Not a cost when** says when to drop it, and **Steps** points at Part 4.

**History is the strongest evidence.** For a region you suspect, run:

```bash
git log --format='%h %ad %s' --date=short -L <start>,<end>:<file>   # every commit that changed these lines
git log --format='%h %s' -i -E --grep='fix|bug|hotfix|revert|regression' -- <file>
git blame -w -C -L <start>,<end> <file>                              # who and when, ignoring whitespace and moves
```

Three bug fixes in one function's lines in a year is a stronger finding than any metric.

### LONG — Long functions

- **Looks like:** a function much longer than the codebase's typical one, doing several things in sequence, often with comments as section headers.
- **Evidence:** its length against the file's and codebase's median function length, the sections it has, and the bug fixes inside it.
- **Not a cost when:** it is one flat, irreducible sequence, such as a table of mappings, a state machine written out, or a builder chain, and it rarely changes.
- **Steps:** extract function, separate pure logic from I/O.

### RESP — Several responsibilities

- **Looks like:** one file or class that parses, decides, stores and formats. Groups of functions that share no data with the other groups. Imports from unrelated areas, such as HTTP, SQL and templating in one module.
- **Evidence:** the responsibilities, each with its line ranges and the names that belong to it. Which callers use which group. Commits that touched only one group.
- **Not a cost when:** the file is the codebase's deliberate place for that combination, such as a feature module in a feature-sliced layout, and it is small.
- **Steps:** split module, move to where it's used.

### NEST — Deep nesting

- **Looks like:** four or more levels of `if`, `for` and `try` inside a function. Arrow code. An `else` far from its `if`.
- **Evidence:** the deepest point (`path:line`) and its depth, and the conditions on the path to it.
- **Not a cost when:** the nesting mirrors the data, such as walking a tree, and is short.
- **Steps:** guard clauses, extract function.

### DUP — Duplication

- **Looks like:** the same block in two or more places, with small differences. A fix that had to be made twice: the same commit touching both copies, or one copy fixed and the other not.
- **Evidence:** each copy's location and a short diff between them. The commits that changed one copy but not the other. `jscpd`, `pylint --enable=duplicate-code` or `dupl` output, if installed.
- **Not a cost when:** the copies are meant to diverge, such as two API versions, or sit across a boundary that must not share code.
- **Steps:** extract function, then call it from each copy. Unify only where the differences are parameters.

### COUP — Temporal coupling

- **Looks like:** a coupled pair from the ranking. A change in this file that keeps needing a change in another. Shared knowledge, such as a magic string, a field order or a protocol, known in both places.
- **Evidence:** the pair, its count and share, two or three commits that touched both, and the knowledge they share (`path:line` in each).
- **Not a cost when:** the pair is a file and its test, an interface and its implementation, or a feature that landed once across both.
- **Steps:** move to where it's used, introduce a shared constant or type, extract function into the module both use.

### STATE — Hidden global state

- **Looks like:** module-level mutable variables, singletons, caches, class attributes mutated by instances, environment or config read deep inside logic, functions that depend on call order.
- **Evidence:** the state, every place that writes it and every place that reads it. Tests that have to reset it.
- **Not a cost when:** it is an immutable constant, or a deliberate, documented process-wide resource such as a connection pool or a logger.
- **Steps:** pass it as a parameter, separate pure logic from I/O, introduce a parameter object.

### NAME — Unclear names

- **Looks like:** names that say nothing (`data`, `process`, `handle2`), names that lie about what the code does, one concept under two names, two concepts under one.
- **Evidence:** the name, what the thing actually does, and the codebase's word for it, with an example.
- **Not a cost when:** the name matches an external API, a protocol or the domain's own term.
- **Steps:** rename. Public names are B.

### MIX — Mixed abstraction levels

- **Looks like:** a function that calls `place_order(cart)` on one line and slices bytes or builds SQL by hand on the next. Business rules next to string formatting.
- **Evidence:** the high-level and low-level lines side by side, with `path:line`.
- **Not a cost when:** the function is short and the low-level part is one line.
- **Steps:** extract function, so each function stays at one level.

### TYPE — Conditionals on type that grow

- **Looks like:** `if kind == "a" … elif kind == "b" …`, `switch (type)`, `isinstance` chains, the same switch repeated in several functions. New features add a branch to each.
- **Evidence:** every switch on the same discriminator (`rg -n '<discriminator>'`), and how many branches the history added and when.
- **Not a cost when:** the set of cases is closed and small, such as the days of a week, or the language's idiom is pattern matching over a sealed type.
- **Steps:** replace with a lookup table, or with polymorphism where the codebase already uses classes that way.

---

## Part 3 — Verifying findings

Try to disprove each finding before it is kept.

| Signal | Disprove it by |
|---|---|
| LONG | Reading the whole function. Is it one irreducible sequence? Is it long compared with this codebase, not with a rule of thumb? |
| RESP | Checking whether the groups really share no data and whether callers use them separately. Shared state between the groups makes the split a redesign. |
| NEST | Checking that guard clauses or extraction would actually flatten it without duplicating conditions. |
| DUP | Diffing the copies line by line and comparing edge cases: empty, null, errors, ordering, time zones. Differences that matter make unifying B, or drop the finding. |
| COUP | Reading the commits behind the count. Were they one feature landing once, or repeated paired changes? Is one file the other's test or implementation? |
| STATE | Finding every writer. If nothing writes after start-up, it's configuration, not hidden state. |
| NAME | Checking the codebase's word for the concept, and every use of the name, including strings, configs and external clients. |
| MIX | Confirming the low-level code isn't a single call already. |
| TYPE | Counting the switches on the discriminator, and the branches added in the history. One switch that hasn't grown isn't a cost. |

A finding with no history evidence and modest numbers is kept only as `PLAUSIBLE`, and its steps go last in the plan.

---

## Part 4 — The refactoring catalog

Use the refactorings the codebase already uses. Before proposing one, find an example of that shape elsewhere in the codebase, or in `docs/conventions.md` or `docs/patterns.md`. A step without a precedent is still possible, but it says so in the plan.

| Refactoring | Fits when | Doesn't fit when | Keeps behavior if | Class |
|---|---|---|---|---|
| **Extract function** | A block inside a long function has one job and few inputs. | The block reads and writes many locals, or `return`s, `break`s or `yield`s out of the middle. | Same inputs in, same outputs and exceptions out. Evaluation order and short-circuiting unchanged. No captured variable changes meaning. | P |
| **Guard clauses** | Nested `if`s where the `else` is an early exit. | The branches have side effects whose order would change. | Conditions are evaluated in the same order with the same side effects. Each exit returns the same value as before. | P |
| **Rename** | A private name says nothing or lies. | The name is exported, serialized, logged and parsed, or used in config or reflection. | Every use is renamed, including strings, templates, configs and `__all__`. | P private, B public |
| **Move to where it's used** | A function or constant is used only by another module, or is the knowledge two coupled files share. | It is part of the module's public API. | All importers are updated in the same step. No import cycle appears. Module-level side effects on import are unchanged. | P internal, B public |
| **Split module** | Groups of functions with no shared data, used by different callers. | The groups share mutable state, or the language makes the split a public API change. | The old module re-exports what callers import, or every importer is updated in the same step. Import order side effects are unchanged. | P with re-export, B without |
| **Introduce parameter object** | The same three or more parameters travel together through several functions. | Only one function takes them, or callers build them in different ways. | It is built at the call sites from the same values. Defaults stay the same. Nothing mutates it where the old code didn't. | P private, B public |
| **Separate pure logic from I/O** | Decisions are tangled with reading files, the network, the clock or the database. | The I/O is a single call at the edge already. | I/O happens in the same order, the same number of times, with the same error handling. The pure part gets the same values it read before. | P |
| **Pass state as a parameter** | A function reads module-level state or the environment deep inside. | Many callers would have to thread it through layers that don't use it. | Every caller passes what the function read before, at the time it read it. | P |
| **Replace conditional with lookup table** | A chain maps a key to a value or a function, with no other logic per branch. | Branches differ in more than the value, or the order of checks matters, such as overlapping ranges. | The missing-key case behaves exactly like the old `else`, including raising. Keys compare the same way (case, types). | P |
| **Replace conditional with polymorphism** | The same type switch appears in several functions, and the codebase already models variants with classes or interfaces. | There is one switch, or the codebase uses plain data and functions. | Each variant's method does exactly its old branch. The default branch is kept. Construction sites create the right variant. | P internal, B public |
| **Consolidate duplicates** | Copies differ only in values that can be parameters. | Copies differ in edge-case behavior. | Each call site passes what its copy hard-coded. Diffs of edge cases are covered by tests. | P |
| **Inline** | A wrapper only forwards, or an indirection hides what happens. | It is public, or a seam that tests use. | No behavior was in the wrapper: no defaults, conversions or error handling. | P private, B public |

**Behavior-changing (B) in any form:** a changed public signature or export, a changed error type or message that callers or users see, changed logging that someone parses, a change in the order of observable side effects, a change in performance someone depends on, and any fix of a suspected bug.

**Report only (N):** a redesign that needs a decision, such as splitting a service, changing a data model, or picking between two architectures. Describe the option and what it would cost.

---

## Part 5 — The safety net

**Measure coverage of the code the plan touches,** with the project's tool if it's installed:

| Ecosystem | Command |
|---|---|
| Python | `pytest --cov=<package.module> --cov-branch --cov-report=term-missing <tests>` (pytest-cov), or `coverage run -m pytest <tests> && coverage report -m --include=<file>` |
| JS / TS | `npx vitest run --coverage --coverage.include=<file>` or `npx jest --coverage --collectCoverageFrom=<file>` |
| Go | `go test -coverprofile=<work>/cover.out ./<pkg>/... && go tool cover -func=<work>/cover.out` |
| Rust | `cargo llvm-cov --text` or `cargo tarpaulin --out Stdout` |
| Java / Kotlin | JaCoCo through the build: `./gradlew test jacocoTestReport` or `mvn test jacoco:report` |
| Ruby | SimpleCov, when the test helper loads it: run the suite and read `coverage/` |
| C# | `dotnet test --collect:"XPlat Code Coverage"`, then read the Cobertura file |

Write coverage output to `<work>` where the tool allows it. Without a tool, list each public function and the tests that call it, and say coverage was read, not measured.

**What to cover.** Every public function, method, endpoint or CLI command whose body a step touches, and every branch a step moves. Line coverage alone isn't enough for a step that reorders conditions. Branch coverage, or a test per branch, is.

**Characterization tests.**
- Drive the code through its public surface, not private helpers. They have to survive the refactoring.
- Use representative inputs, edges (empty, null, zero, negative, very large, unicode, duplicates) and the inputs from the bug-fix commits found in Step 3.
- Assert what the code does now: return values, raised errors and their messages, writes to files, databases or mocks of external systems, and log lines someone depends on. Write the expected value by running the code, not by reading the requirement.
- A value that looks wrong is pinned as it is, with a comment such as `# characterization: current behavior, looks wrong, see hotspots report`. Never assert what the code should do. Never fix the code here.
- Make them deterministic. Fix the clock, the random seed and the ordering of sets and dicts. Run them twice.
- Mark them clearly, so nobody mistakes them for a specification.

| Ecosystem | Name and mark | Snapshot or approval option |
|---|---|---|
| Python (pytest) | `tests/.../test_<module>_characterization.py`, `@pytest.mark.characterization` if the project registers markers | `syrupy`, `pytest-snapshot`, `approvaltests` if installed |
| JS / TS (jest, vitest) | `<module>.characterization.test.ts`, `describe("characterization: <module>")` | `toMatchSnapshot()`, `toMatchInlineSnapshot()` |
| Go | `<file>_characterization_test.go`, `TestCharacterization<Func>` with table-driven cases | golden files under `testdata/` |
| Rust | `tests/characterization_<module>.rs` or a `mod characterization` | `insta` if it's a dependency |
| Java / Kotlin | `<Class>CharacterizationTest`, `@Tag("characterization")` | ApprovalTests if present |
| Ruby (RSpec) | `spec/.../<module>_characterization_spec.rb`, `describe "characterization"` | `rspec-snapshot` if present |
| C# (xUnit, NUnit) | `<Class>CharacterizationTests`, `[Trait("Category", "Characterization")]` | `Verify` if present |

Use a snapshot library only if the project already has it. Otherwise write explicit assertions. They read better in review, and adding a dependency isn't this skill's job.
