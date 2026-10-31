# Mutants

Part 1 sets up the scratch tree, finds the covering tests and runs the baseline (Step 2). Part 2 is the operator catalog and how to choose mutants within a budget (Step 3). Part 3 runs them, with a tool or by hand (Steps 3, 6 and 7). Part 4 verifies the survivors and lists weak tests (Step 4). Each part ends with the output contract of the file it writes.

## Part 1 — The scratch tree and the baseline

### Make the scratch tree

```bash
git worktree add --detach <work>/tree <head sha>
# an uncommitted target: bring the changes over too
git diff HEAD --binary | git -C <work>/tree apply --binary
# and copy each untracked file in scope to the same path under <work>/tree
```

A worktree has only tracked files. Whatever the tests need that git ignores has to be pointed at, never installed:

| Ecosystem | Make the tree runnable |
|---|---|
| Python | Use the repository's interpreter (`<repo>/.venv/bin/python`, or the one its tooling names) directly, not `uv run` or `poetry run`, which may sync or install. Set `PYTHONPATH=<tree>/<src dir>` so the tree's code wins over an editable install of the package, which would otherwise point back at the user's repo. |
| JS / TS | `ln -s <repo>/node_modules <work>/tree/node_modules`, and the same for each workspace package's `node_modules` in a monorepo. Workspace links inside `node_modules` point at the user's repo, so a test that imports a sibling package by name runs the user's copy, which is fine as long as the target isn't that package. |
| Go | Nothing. The module cache is shared. Always pass `-count=1`, or Go reuses cached passes. |
| Rust | `CARGO_TARGET_DIR=<work>/target` and `--offline`. The first build is a full one, so count it in the budget. |
| Java | Maven and Gradle caches are shared. Use `mvn -o` or `gradle --offline` so nothing is downloaded. |
| Ruby | Run `bundle exec` from the tree with the repository's bundle config. If gems are vendored in the repo (`vendor/bundle`), symlink that directory. |

**The canary.** Before trusting any result, take one function the covering tests certainly call, make it raise (or panic, or throw) on its first line in the scratch tree, and run its covering tests. They must fail. Restore it. If they pass, the tests are running some other copy of the code, such as an editable install, a workspace link or a stale build, and every mutant would look like a survivor. Fix the setup before going on, and record the canary in `2-baseline.md`.

### Find the covering tests

Use a coverage tool when the project already has one, run in the scratch tree:

| Ecosystem | Command | What it gives |
|---|---|---|
| Python, pytest-cov | `pytest --cov=<pkg> --cov-branch --cov-context=test --cov-report= <tests>` then `coverage json --show-contexts -o <work>/cov.json` | Per line, the test ids that ran it (`files[path].contexts[line]`) |
| Jest | `npx jest --listTests --findRelatedTests <file>` for the tests, `npx jest --coverage --coverageReporters=json --collectCoverageFrom=<file> <tests>` for the lines | Related test files by import graph, and covered lines per file, not per test |
| Vitest | `npx vitest related <file> --run` · `npx vitest run --coverage.enabled --coverage.reporter=json --coverage.include=<file>` | The same |
| Node test runner, c8 | `npx --no-install c8 --reporter=json --include=<file> node --test <tests>` | Covered lines per file |
| Go | `go test -count=1 -coverprofile=<work>/cover.out ./<pkg>/...`, then `go tool cover -func=<work>/cover.out` | Covered blocks per package. Per test, re-run with `-run '^TestX$'`. |
| Rust | `cargo llvm-cov --json` if installed | Covered lines per crate |
| Java | The JaCoCo report, if the build already produces one | Covered lines per class |
| Ruby | SimpleCov's `coverage/.resultset.json`, if configured | Covered lines per file |

Without a coverage tool, find the tests by reading:
1. Test files that import the module, or the package that re-exports it (`rg -l "from <pkg>.<mod> import|import .*<mod>|require\(.*<mod>"`).
2. Tests named after the file (`test_<mod>.py`, `<mod>.test.ts`, `<mod>_test.go`, `<Mod>Test.java`, `<mod>_spec.rb`).
3. Tests that call the changed functions by name (`rg -n "<function>\(" <test dirs>`).

Mark each covering-test set as found by coverage or by reading. A line that only reading says is covered may still be not covered. Step 3's outcomes will tell.

### Run the baseline

Run the covering tests twice in the scratch tree, the way each mutant will run them:

- Select only the covering tests: pytest node ids or `-k`, `jest --runTestsByPath <files>`, `vitest run <files>`, `go test -count=1 -run '^(TestA|TestB)$' ./<pkg>`, `cargo test -p <crate> <filter>`, `mvn -o -q test -Dtest=<Class>`, `bundle exec rspec <file>`.
- Stop at the first failure, so a killed mutant costs little: `pytest -x`, `jest --bail`, `vitest --bail=1`, `go test -failfast`, `mvn -Dsurefire.skipAfterFailureCount=1`, `rspec --fail-fast`.
- A test that fails in either run is excluded from every mutant's command (`--deselect`, `-t` with a negative pattern, `-skip` in Go 1.20+). One that fails in one run only is flaky, and is excluded too. Both are listed.

### Detect a mutation tool

Use one only if it's already installed for this project (Part 3 lists how to tell). `--tool` overrides. A tool that can't be scoped to the target files, or that would install something on first run, is passed over for `manual`.

**Budget.** The per-mutant cost is the covering tests' baseline time, plus the build or syntax check. Mutants that fit ≈ budget in seconds × 0.8 ÷ per-mutant cost, and a tool's own overhead comes on top.

**Output contract for `2-baseline.md`:**

```
TEST CONVENTIONS (from <docs/conventions.md CONV-n | the files below>)
- Framework and runner: <…> · Layout and naming: <…>
- Fixtures and setup: <…> · Mocking: <what gets mocked, e.g. only HTTP and the clock>
- Assertions and parametrization: <…>
- Copy the shape of: <path:line>

SCRATCH TREE
Path: <work>/tree at <sha> · uncommitted applied: yes | no
Runnable by: <e.g. <repo>/.venv/bin/python with PYTHONPATH=src | node_modules symlinked>
Canary: <file:line made to raise> → <killed by <test> | SURVIVED: setup fixed by …>

COVERING TESTS
| Source file | Covering tests | Found by | Changed lines run by a test |
|---|---|---|---|
| src/money.py | tests/test_money.py (14 tests) | coverage contexts | 22 of 25 (not: 40-42) |

BASELINE
| Source file | Command | Run 1 | Run 2 | Seconds |
|---|---|---|---|---|
Already failing (excluded): <test ids, or none>
Flaky (excluded): <test ids, or none>
No tests at all: <files, or none>

MUTATION TOOL
Installed: <tool and version, or none> · Using: <tool | manual: why>
Budget: <min> · per-mutant cost about <s>s · about <n> mutants fit
```

---

## Part 2 — Operators and choosing

### The catalog

| Code | Operator | Before → after | Survives when the tests… |
|---|---|---|---|
| NEG | Negate a conditional | `if valid:` → `if not valid:` · `a == b` → `a != b` · `if (ok)` → `if (!ok)` | only try one outcome of the branch |
| BND | Shift a boundary | `<` ↔ `<=` · `>` ↔ `>=` · `len(xs) > 0` → `len(xs) > 1` | never use the boundary value itself |
| ARITH | Swap arithmetic | `+` ↔ `-` · `*` ↔ `/` · `+=` → `-=` · `//` → `/` | use values where the result doesn't show it (0, 1) |
| LOG | Swap and/or | `a and b` ↔ `a or b` · `&&` ↔ `\|\|` | never have exactly one side true |
| RET | Replace a return value | `return total` → `return 0` / `None` / `null` / `nil` / `""` / `[]` / `{}` · `True` ↔ `False` · Go `return v, nil` → `return zero, nil` · Rust `Ok(v)` → `Ok(Default::default())` | don't check what comes back, or only that it isn't null |
| STMT | Remove a statement or call | delete `cache.invalidate(key)`, `self.count += 1`, `repo.save(order)` (Python: `pass` when it's the only statement) | don't check the side effect |
| RAISE | Remove a raise or throw | `raise ValueError(…)` → removed · `throw new X()` → removed · Go `if err != nil { return …, err }` → removed · Rust `?` → `.unwrap_or_default()` | never take the error path |
| CONST | Change a constant | `MAX_RETRIES = 3` → `2` / `4` · `0` → `1` · `True` → `False` · `"utf-8"` → `"ascii"` | don't pin a value that matters |
| LOOP | Skip the loop body, or break early | first statement of the body becomes `continue` / `break` · `for x in xs` → `for x in xs[:1]` | only use empty or one-element inputs |
| ARGS | Swap arguments of the same type | `transfer(src, dst)` → `transfer(dst, src)` · `range(a, b)` → `range(b, a)` | use symmetric or equal values |
| AWAIT | Remove an await | `await save(x)` → `save(x)` (Python: the coroutine never runs; JS: the promise isn't waited for) | don't check the effect happened, or don't wait for it |
| OBO | Off by one in a slice or range | `xs[:n]` → `xs[:n-1]` · `range(n)` → `range(1, n)` · `slice(0, n)` → `slice(0, n + 1)` · Rust `0..n` ↔ `0..=n` | never check the first or last element |
| GUARD | Delete a default or guard clause | remove `if not items: return []` · remove `x = x or default` · `a ?? b` → `a` · Rust `.unwrap_or(d)` → `.unwrap()` · default `timeout=30` → `timeout=None` | never pass the empty, missing or default case |

**Language notes.**
- **Python and Ruby:** check each mutant compiles (`python -m py_compile <file>`, `ruby -c <file>`) and give that as the mutant's `build`, so a typo counts as unviable, not killed.
- **JS / TS:** `node --check <file>` for JS. For TS, a runner that strips types (Vitest, esbuild-based Jest) runs ill-typed mutants. That's fine: the test still judges behavior. Where the project type-checks in its tests (ts-jest), keep mutants well-typed.
- **Go:** `if err != nil` → `if err == nil` usually crashes on the next line and is killed by any test. Prefer RAISE on error paths and BND and RET on the logic. Use `go vet ./<pkg>` as the build.
- **Rust:** mutants must type-check. Use `cargo check --tests --offline` as the build. RET uses `Default::default()` or a value of the right type.
- **Java:** PIT's operators map to these: CONDITIONALS_BOUNDARY (BND), NEGATE_CONDITIONALS (NEG), MATH (ARITH), the RETURNS group (RET), VOID_METHOD_CALLS (STMT), INCREMENTS (ARITH). The build is `mvn -o -q compile` or the Gradle equivalent.

**What not to mutate.** Logging calls (except an audit record the code is required to write), comments, imports, type annotations, `__repr__` and debug strings, the wording of user-facing messages, generated code, and test files. These give unobservable mutants or noise. A changed line with nothing else on it is skipped, with the reason counted.

### Choosing within the budget

Prefer the mutant a real bug would look like. An off-by-one, a flipped condition and a forgotten `raise` are mistakes people make. Replacing `+` with `%` mostly isn't.

1. **First pass, one mutant per line with logic,** chosen by what the line is:

   | The line is | First mutant | Then, if the budget allows |
   |---|---|---|
   | A branch condition with a comparison | BND | NEG, LOG |
   | A branch condition without one | NEG | LOG |
   | A return | RET, the value most unlike the real one (`None` for an object, empty for a collection, the other boolean) | a second RET value |
   | A raise, throw or error return | RAISE | — |
   | A guard or default | GUARD | CONST |
   | A loop | LOOP | OBO |
   | A slice or range | OBO | — |
   | Arithmetic | ARITH | CONST |
   | A call made for its effect | STMT | ARGS, AWAIT |
   | A constant that sets behavior | CONST | — |

2. **Second pass, while the budget lasts:** the "then" column for branch conditions and returns, then error paths, then the rest.
3. **Skip low-information mutants:** one that breaks the module on import, one any test of the file would kill, and a third mutant on a line before every line has one.
4. **Order the run** so the most informative mutants go first. A run the budget cuts short then still answers the questions that matter.

**`mutants.jsonl`**, one mutant per line, as `scripts/mutate.py` reads it:

```
{"id": "M14", "file": "src/money.py", "line": 18, "find": "amount < 0", "replace": "amount <= 0", "op": "BND", "fn": "parse_amount", "cmd": "<covering tests, failing and flaky ones excluded>", "build": "<python -m py_compile src/money.py>"}
```

- `find` has to occur exactly once on the line, or across `line` to `end_line` for a multi-line statement.
- `cmd` is `null` for a line no test runs. The mutant is recorded as not covered without running anything.
- `timeout` is left out, so the script uses three times the command's baseline time, at least 10 seconds.
- IDs are never reused, so Steps 6 and 7 can refer back to them.

---

## Part 3 — Running

### With a tool

Run every tool from the scratch tree, never the user's tree: mutmut 2, cosmic-ray and go-mutesting edit files in place. Edit a tool's config only in the scratch tree. Check `--help` for the installed version before relying on a flag below.

| Tool | Installed when | Scoped run | Results |
|---|---|---|---|
| mutmut 2 (Python) | `mutmut --version` prints 2.x | `mutmut run --paths-to-mutate <file> --runner "<cmd>" --use-patch-file <work>/diff.patch` | `mutmut results`, `mutmut show <id>` |
| mutmut 3 (Python) | `mutmut --version` prints 3.x | set `paths_to_mutate` in the tree's `[tool.mutmut]`, then `mutmut run` | `mutmut results`. It mutates whole functions, so keep only mutants on changed lines (`mutmut show <name>`). |
| cosmic-ray (Python) | `cosmic-ray --version` | a `<work>/cr.toml` with `module-path`, `test-command`, `timeout`, then `cosmic-ray init <work>/cr.toml <work>/cr.sqlite`, `cr-filter-git <work>/cr.sqlite` for diff targets, `cosmic-ray exec <work>/cr.toml <work>/cr.sqlite` | `cr-report <work>/cr.sqlite` |
| Stryker (JS / TS) | `node_modules/.bin/stryker` exists | `npx --no-install stryker run --mutate "src/a.ts:10-20,src/b.ts" --reporters json,clear-text --coverageAnalysis perTest` | `reports/mutation/mutation.json` |
| gremlins (Go) | `gremlins --version` | `gremlins unleash ./<pkg> --output <work>/gremlins.json`, plus `--diff <base>` if the version has it | the JSON file |
| go-mutesting (Go) | `go-mutesting --help` | `go-mutesting <file.go>` | its PASS/FAIL lines per mutant |
| cargo-mutants (Rust) | `cargo mutants --version` | `cargo mutants --in-diff <work>/diff.patch` or `--file <path>`, with `--re '<fn>'` to narrow, `--output <work>/cm`, `--timeout <s>` | `<work>/cm/mutants.out/outcomes.json`, `missed.txt`, `caught.txt` |
| PIT (Java) | `pitest-maven` or the Gradle `pitest` plugin is already in the build | `mvn -o org.pitest:pitest-maven:mutationCoverage -DtargetClasses=<Class> -DtargetTests=<TestClass> -DoutputFormats=XML` · Gradle: set `targetClasses` in the tree's build file, then `./gradlew --offline pitest` | `target/pit-reports/mutations.xml` (filter to changed lines) |
| mutant (Ruby) | `bundle exec mutant --version` | `bundle exec mutant run --include lib --require <lib> --integration rspec --since <base> '<Namespace>*'` (`--use rspec` on older versions) | its report |

Write the diff for `--use-patch-file` and `--in-diff` with `git diff <base> <head> -- <files in scope> > <work>/diff.patch`, or `git diff HEAD` for uncommitted work.

**Map the tool's statuses** onto the skill's:

| Skill | mutmut | Stryker | PIT | cargo-mutants | gremlins | cosmic-ray |
|---|---|---|---|---|---|---|
| killed | killed | Killed | KILLED | caught | KILLED | killed |
| survived | survived | Survived | SURVIVED | missed | LIVED | survived |
| not covered | no tests | NoCoverage | NO_COVERAGE | — | NOT COVERED | — |
| timeout | timeout | Timeout | TIMED_OUT | timeout | TIMED OUT | incompetent (timeout) |
| unviable | — | CompileError | NON_VIABLE | unviable | NOT VIABLE | — |

A status the table doesn't have (mutmut's "suspicious", PIT's RUN_ERROR) gets the mutant re-run by hand with `mutate.py`. Give tool mutants IDs `M<n>` in the order the tool lists them, and keep the tool's own ID in the note column.

### By hand

```bash
python3 <skill dir>/scripts/mutate.py check --tree <work>/tree --mutants <work>/mutants.jsonl
python3 <skill dir>/scripts/mutate.py run --tree <work>/tree --mutants <work>/mutants.jsonl \
    --out <work>/results.jsonl --budget <min>
python3 <skill dir>/scripts/mutate.py summary --mutants <work>/mutants.jsonl --out <work>/results.jsonl
```

- `check` confirms every mutant applies. Fix or drop those that don't before running.
- `run` runs each distinct command once on the unmutated tree first. Then, one mutant at a time, it applies the edit, runs the build and the covering tests with the timeout, and restores the file, checking it byte for byte. It refuses a repository's main working tree. Running it again with the same `--out` resumes, so a budget that runs out can be extended later.
- `summary` prints the per-file table for `3-mutants.md`.
- Exit code 2 means a file couldn't be restored. Stop, and look at the tree before anything else runs in it.
- The killing test is in each result's `tail`. Read it: a mutant "killed" by an import error or a fixture crash was killed by accident. Re-check that its build ran.

**Parallel.** One scratch tree per group (`git worktree add --detach <work>/tree-<group> <sha>`), one `mutate.py run` per tree with its own `--out`, and the files of different groups never overlap. Only run groups at the same time when their tests share no database, port, temp path, cache directory or container. Merge the result files before `summary`.

**Output contract for `3-mutants.md`** (or `3-mutants-<group>.md`):

```
Run: <tool command | mutate.py run …> · <n> chosen · <n> run · <n> not run (budget) · <minutes>
Lines: <n> with logic · <n> with a mutant · <n> skipped: <reason: count, …>

SCORE (before Step 4)
<the summary table, per file, then per function for functions with survivors>

MUTANTS
| ID | Where | Function | Op | Change | Status | Killed by / note |
|---|---|---|---|---|---|---|
| M14 | src/money.py:18 | parse_amount | BND | `amount < 0` → `amount <= 0` | survived | |
| M15 | src/money.py:21 | parse_amount | RET | `return value` → `return None` | killed | test_parse_amount_basic |
(every chosen mutant, "not run" included)

KILLS NOTHING: <tests that ran against three or more mutants and killed none, or none>
```

---

## Part 4 — Verifying survivors

### Equivalent

A mutant is equivalent only when no input can tell it from the original. Name the rule and show it holds here:

| Rule | Example | Holds only if |
|---|---|---|
| The other value can't reach the condition | `if x is None: return` then `if x is not None and y:` → `if y:` | nothing between the two lines can set `x` to `None` |
| A loop index that only steps by one | `while i < n` → `while i != n` | `i` starts at or below `n` and only ever increases by 1 |
| Identity arithmetic | `x * 1` → `x / 1`, `x + 0` → `x - 0` | the types make them the same (not integer vs. float division) |
| Commutative arguments | `max(a, b)` → `max(b, a)`, `a == b` → `b == a` | no side effects or ordering in the arguments |
| A result nobody reads | RET on a private function whose every caller ignores the return value | it's private: a public function's return value is its contract |
| Dead code | any mutant in a branch no input reaches | the dead code is reported too, since it's a finding of its own |
| An effect redone right after | STMT on a cache set that the next line sets again | nothing reads in between, and the redo always runs |
| A clamp that absorbs the change | `max(0, n - 1)` → `max(0, n - 2)` where `n` is always 0 or 1 | the range is guaranteed by a type or a validator, not by today's callers |

When in doubt, it isn't equivalent. Look for an input that tells the two apart, and if there is one, it's a gap.

### Observable

Follow the changed value to where a caller could see it: the return value, an error raised, state written to an object, a database or a file, output, or a call to an outside system. If it reaches one of those for some input, the mutant matters.

**Unobservable** is narrower than equivalent. The behavior differs, but only in what the code doesn't promise anyone:
- the wording of a log or debug message (not an audit record or a log line a test, alert or parser reads)
- timing, retries or a cache size that changes speed but not results
- the internal state of an object that no method exposes

Unobservable mutants stay in the score and get no test. Testing them would pin the code's internals.

### Not covered

Confirm that no test runs the line: search the tests for the function by name, and for the module path in mocks and patches. Coverage tools miss code run in subprocesses, worker threads and forked processes. A line some test does run moves back to survived and is judged as above.

### Skeptic brief

Give each skeptic only:
- the repository path and the scratch tree path
- the function, its location, and its mutants: each one's ID, line, original and mutated code
- the claim for each, survived as a gap, equivalent with its rule, or unobservable with its reason
- the task: try to disprove each claim, and answer `GAP`, `EQUIVALENT` or `UNOBSERVABLE` per mutant, with `EVIDENCE`. That is an input with the two outcomes, or the reason no such input exists.
- that it may run code only in the scratch tree, and must restore any file it changes

### Weak tests

List what Steps 2 to 4 ran into. Don't go hunting through the whole suite, and don't fix anything.

| Pattern | How it looks |
|---|---|
| No assertions | A test that calls the code and checks nothing. No `assert`, `expect`, `assertEquals`, `t.Error`, `assert_*`. |
| Asserts its own mock | `repo.get.return_value = order` … `assert result == order`, where the unit only passes the value through. `assert_called_with` on the arguments the test itself supplied, with the unit under test mocked. |
| Assertion-free snapshot | `toMatchSnapshot()` or `snapshot.assert_match` as the only check, on output that is mocked, or a snapshot file written in the same change and never reviewed. |
| Swallows the failure | `try: … except: pass` or `catch {}` around the assertions. `pytest.raises(Exception)` around more than the call. Asserts inside an `if` the test data never enters. |
| Kills nothing | Ran against three or more mutants of the code it tests and killed none. |

**Output contract for `4-verification.md`:**

```
| Mutant | Step 3 | Checked how | Verdict | Distinguishing input, or the reason |
|---|---|---|---|---|
| M14 | survived | traced caller api/pay.py:40, which passes user input | GAP | `parse_amount("0")`: original returns 0, mutant raises ValueError |
| M17 | survived | loop at :33 | EQUIVALENT | index loop: `i` starts at 0, steps by 1, `n ≥ 0` |
| M19 | survived | log line at :55, no test, alert or parser reads it, not an audit record | UNOBSERVABLE | only the message wording changes |
| M20 | not covered | `rg -n "refund\(" tests/` finds nothing | GAP (not covered) | any call to `refund` |

SCORE (after Step 4): (killed + timeout) <n> / (killed + timeout + survived + not covered <n> − equivalent <n>) = <x>% · per file: <…>
SKEPTICS: <function → verdicts that changed, or "inline mode, none run">

WEAK TESTS
| Test | Pattern | Evidence |
|---|---|---|
| tests/test_pay.py::test_charge | asserts its own mock | :40 sets `gateway.charge.return_value`, :44 asserts that value |
```
