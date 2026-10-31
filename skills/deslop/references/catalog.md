# Slop catalog

Part 1 is done once per run, in Step 2. Part 2 is the detection pass in Step 3. Part 3 is how each family's findings are verified in Step 4. Each part ends with the shape of the file it writes.

## Contents

- Part 1 — The baseline
- Part 2 — The families: CMT, DEF, ERR, SPEC, DUP, DEAD, FAKE, API, TEST, NAME, VERB, LOG, DRIFT, BLOAT
- Part 3 — Verifying findings
- Ratings and fix classes

## Ratings and fix classes

Every finding gets a severity and a fix class.

| Severity | Meaning |
|---|---|
| 🔴 **Hides a bug** | The slop makes the code wrong or hides that it is: placeholders, fake implementations, hallucinated APIs, swallowed errors, tests that can't fail. |
| 🟠 **Costs** | Makes the code harder to change or easy to break later: speculative abstractions, duplication, reinvented helpers, drift from conventions, misleading names or comments. |
| 🟡 **Noise** | Makes the code longer without making it worse: narrating comments, verbose idioms, generic names, leftover blank structure. |

| Class | Meaning | Applied |
|---|---|---|
| **S — safe** | Can't change behavior: deleting a comment, an unused import, a debug print, commented-out code. Renaming a local variable. | With plan approval, or with `--auto` |
| **P — preserving** | Changes structure while keeping behavior, and you can say why it's the same: inlining a wrapper that only delegates, reusing a helper with identical semantics, flattening nesting. Tests confirm it. | With plan approval, or with `--auto` |
| **B — behavior-changing** | Anything callers, users or tests could observe: errors that now propagate, a check removed that could fire, a placeholder replaced, a fixed API call, a changed signature, a strengthened test assertion. | Only with the user's yes to that fix |
| **N — report only** | Needs a decision the code can't make: a design to choose, a real implementation to write, a requirement to look up. | Never; it goes in the report |

When unsure between two classes, take the stricter one.

---

## Part 1 — The baseline

Read enough of the codebase to answer these questions with examples, `path:line`, not impressions.

- **Comments and docs.** How many comments per hundred lines in established files? Is there a docstring on every function, on public ones only, or rarely? What style (Google, NumPy, JSDoc, none)? Do comments say *why* or *what*?
- **Errors.** Does the codebase let exceptions propagate to a boundary handler, or catch locally? Does it use custom error types, result types, error wrapping (`raise … from`, `fmt.Errorf("…: %w")`)? Where is the boundary: a request handler, a CLI main, a job runner?
- **Validation.** Where are inputs validated: at the edge (schemas, request models, typed parsers) or at each layer? What do types already guarantee (strict null checks, `Optional`, non-nullable fields)?
- **Logging.** Which library and logger setup? Which levels, for what? Structured or format strings? Does a middleware already log requests and unhandled errors?
- **Structure.** Typical function and file length. Are there interfaces or base classes, and how many implementations does each have? How are dependencies passed: constructors, module functions, a container?
- **Naming.** Case style, prefixes and suffixes, abbreviations the codebase uses, words it avoids.
- **Tests.** Framework, fixtures, how much is mocked, whether parametrization is used, naming, where tests live.
- **Reuse index.** For each job the target does, list the existing utility or dependency that does it, with its `path:line` or import. Include standard library and framework features the codebase already uses.

**Output contract for `2-baseline.md`:**

```
CONVENTIONS
- Comments: <density, style, why/what> — e.g. <path:line>
- Errors: <style, boundary> — e.g. <path:line>
- Validation: <where, what types guarantee>
- Logging: <library, levels, structure, what middleware logs>
- Structure: <function/file size, abstractions, DI>
- Naming: <style>
- Tests: <framework, fixtures, mocking, parametrize>

REUSE INDEX
| Job | Use this | Where |
|---|---|---|

TOOLS
| Tool | Command | Ran on scope | Result |
|---|---|---|---|
(formatter, linter, type-checker, dead-code, duplicates, tests, coverage; "not installed" where absent)

BASELINE TESTS
Command: <…> · <n> passed · <n> failed · <n> skipped · <duration>
Already failing: <test ids, or none>
```

---

## Part 2 — The families

For each family, read **Looks like** to know what to hunt, use the **Signals** to search for it, and check **Not slop when** before recording anything. **Fix** gives the usual fix and its class.

Search with ripgrep over the files in scope, and read every hit in context. A signal is where to look, not a finding.

### CMT — Comments and docs

**Looks like**
- Comments that say what the next line plainly does, like `# increment the counter` or `// loop over users`.
- Comments that restate a name, like `# User repository` above `class UserRepository`.
- Comments addressed to a reader of the chat rather than the code: "Here we now…", "As requested…", "Updated to…", "New:", "Fixed:", "Changed from X to Y", "This is the key part".
- Changelog history written into the code.
- Section banners inside short functions, like `# --- Step 1: validate ---`.
- Emoji in comments.
- Docstrings that only repeat the signature (`Args: user_id: The user ID`) on private or trivial functions in a codebase that doesn't do that.
- `Returns: None` on functions that return nothing.
- Comments that disagree with the code.
- Markdown files nobody asked for, such as `IMPLEMENTATION_NOTES.md` or `SUMMARY.md`.

**Signals**
- `rg -n '^\s*(#|//|\*)\s*(Here|Now|First|Then|Next|Finally|This (function|method|class|code)|We |Let.s|Note:|Important:|Updated|Changed|Fixed|New:|Added)'`
- Comment lines next to code lines with the same words.
- Comment density well above the baseline.
- New `.md` files in the change.

**Not slop when**
- The comment says why: a constraint, a workaround, a link to an issue, a non-obvious invariant, a unit, a performance reason.
- The codebase documents everything that way.
- It's a public API doc that a doc generator publishes.
- It's a license header or a lint pragma.

**Fix**
- Delete it (S).
- A stale comment that disagrees with the code: fix it to match the code (S). If it's unclear which one is right, record a question (N).
- An unrequested markdown file: report it (N). It may be wanted.

### DEF — Defensive overkill

**Looks like**
- Null or undefined checks on values the type system, the caller or a validator already guarantees.
- `isinstance` or `typeof` checks on typed parameters.
- Re-validating at each layer what the edge already validated.
- `if x is not None and x != "" and len(x) > 0`.
- `.get(key, default)` on a key that is always present, or that should fail loudly when missing.
- Optional chaining (`a?.b?.c`) on non-optional data.
- `try` around code that can't raise what is caught.
- Fallback values that turn a bug into a wrong answer.
- Timeouts and retries around in-process calls.

**Signals**
- `rg -n 'is not None|!= null|!== undefined|\?\.|isinstance\(|typeof .* ===|\.get\([^)]*,'`
- `try` blocks of one or two lines.
- The same field validated in the handler, the service and the model.

**Not slop when**
- The value really can be missing: external input, I/O, a nullable column, a public library boundary.
- The check guards a trust boundary.
- The codebase validates at every layer deliberately.

**Fix**
- Remove a check that can provably never fire (P). Say why in the plan.
- Remove a fallback or a check that can fire, so the code now fails loudly (B).

### ERR — Swallowed and laundered errors

**Looks like**
- `except: pass` or `except Exception: pass`.
- `catch (e) { console.log(e) }` and carry on.
- Catching broadly and returning `None`, `[]`, `false` or `{}` so the caller can't tell failure from empty.
- Re-raising a new error without the cause (`raise X()` instead of `raise X() from e`, `errors.New` instead of wrapping).
- Generic messages: "An error occurred", "Something went wrong".
- Logging and re-raising at every level, so one failure logs five times.
- Error handling that only exists to print.

**Signals**
- `rg -n 'except( Exception)?( as \w+)?:\s*$' -A2`, then look for `pass`, `return None`, `continue` or a bare log.
- `rg -n 'catch\s*\(\w*\)\s*\{' -A3`
- `rg -n 'if err != nil \{\s*$' -A2`, then look for `return nil` or a log only.
- `rg -n 'error occurred|went wrong|Failed to [a-z]+$'`

**Not slop when**
- The codebase deliberately degrades here, such as a best-effort cache or telemetry, and says so.
- It's the top-level boundary handler.
- The caught error is specific and expected, like `FileNotFoundError` meaning "use the default".

**Fix**
- Narrow the caught type, add the cause, or let the error propagate to the boundary (B).
- Remove duplicate log-and-rethrow layers (P), if the boundary still logs it once.

### SPEC — Speculative generality

**Looks like**
- An interface, ABC or protocol with one implementation.
- A factory, builder, registry or strategy with one product.
- A `BaseX` with one subclass.
- Config options, flags or parameters that every caller sets to the same value, or that nobody sets.
- Generic type parameters used with one type.
- Wrapper classes or functions that only delegate.
- A `Manager`, `Handler`, `Service` or `Helper` class with one method and no state.
- "For future extensibility" layers.
- A plugin system with one plugin.

**Signals**
- `rg -n 'class \w*(Base|Abstract|Interface|Factory|Manager|Handler|Provider|Strategy|Registry)\b|ABC\)|Protocol\)|interface \w+'`, then count the implementations and users of each.
- Functions whose body is a single call with the same arguments.
- Parameters with defaults that no caller overrides.

**Not slop when**
- There's a second implementation in tests that the abstraction exists for, such as a fake for an external service.
- It's an extension point published to other packages.
- The codebase's architecture requires the layer.
- A second implementation is in the same change or in an open plan the user points to.

**Fix**
- Inline the wrapper. Collapse the interface into its implementation. Drop the unused parameter and its default.
  - Private code: P.
  - Public or exported signatures: B.

### DUP — Reinvention and duplication

**Looks like**
- A new helper that does what something in the reuse index already does: date parsing, path joining, retry, deep copy, slugify, chunking, env loading, HTTP wrappers.
- Hand-rolled standard library features.
- Near-identical functions or blocks within the change, or between the change and existing code.
- The same constant or regex defined twice.
- A new dependency for something an existing dependency does.

**Signals**
- New function names compared with the reuse index.
- `jscpd`, `pylint --enable=duplicate-code` or `dupl` if installed.
- New entries in the dependency manifest.

**Not slop when**
- The existing helper has different semantics that matter here: time zones, error behavior, an edge case.
- Duplication across a deliberate boundary, such as separate services or packages that must not depend on each other.

**Fix**
- Call the existing helper and delete the copy.
  - Identical semantics: P.
  - Different edge-case behavior: B.
- Merge the near-duplicates (P).
- Drop a new dependency in favor of an existing one (B), since the lockfile changes.

### DEAD — Dead code and leftovers

**Looks like**
- Unused imports, variables, parameters, functions, classes and files.
- Commented-out code.
- Debug output: `print`, `console.log`, `dbg!`, `fmt.Println`, `pp`, `debugger`.
- Unreachable branches.
- `_old`, `_v2`, `_new`, `_backup`, `_copy` files or functions left next to the live one.
- `if __name__ == "__main__":` demo blocks in library modules.
- Example usage blocks.
- TODOs the change added and then did.

**Signals**
- The linter and dead-code tool output from the baseline.
- `rg -n '^\s*(print\(|console\.(log|debug)|debugger;|fmt\.Print|dbg!|pp )'`
- `rg -n '^\s*(#|//)\s*\w+\s*\(.*\)\s*;?\s*$'` for commented-out calls.
- `rg --files | rg '(_old|_v\d|_new|_backup|_copy|\.bak)\b'`

**Not slop when**
- It's used through reflection, a registry, a decorator, an entry point, a template, a config file, a public export, or a test.
- A `print` is the CLI's output.
- A `__main__` block is a real script entry point.

**Fix**
- Delete it (S). That covers imports, locals, commented-out code, debug output and unreachable code.
- Unused exported functions, parameters and files: P for private code, B for anything public.

### FAKE — Placeholders and fake implementations

**Looks like**
- `pass`, `...`, `TODO: implement`, `NotImplementedError` or `return True  # placeholder` in code the change presents as done.
- Hardcoded return values.
- Mock or sample data in a production path.
- Functions that ignore their parameters.
- "Simplified" versions of a requirement.
- Cases silently skipped with `else: pass` or `default: break`.
- Sleep calls standing in for real synchronization.
- A test switch or mock mode left on.

**Signals**
- `rg -n 'TODO|FIXME|XXX|placeholder|for now|simplified|dummy|mock|fake|sample|hardcoded|NotImplemented|^\s*(pass|\.\.\.)\s*$'`
- Parameters unused in the body.
- Constant returns.
- `sleep(` in non-test code.

**Not slop when**
- It's an abstract method, an intentional no-op hook, or a documented stub in a published interface.
- It's a test double in test code.

**Fix**
- Usually N: the real implementation is a requirement question. Report what's missing and what the code claims.
- If the intended behavior is unambiguous and small, B with approval.

### API — Hallucinated or misused APIs

**Looks like**
- Calls to functions, methods, keyword arguments, options, config keys, CLI flags or environment variables that don't exist in the installed version.
- Imports of modules that aren't installed or don't exist.
- Deprecated APIs where the codebase already uses the replacement.
- Wrong argument order or units, such as seconds for milliseconds.
- Mixing two libraries' APIs.

**Signals**
- Type-checker and linter errors from the baseline.
- Imports not in the manifest.
- Unfamiliar keyword arguments.
- Options read from config that nothing sets.

**Not slop when**
- The API exists in the installed version. Check the installed source, not memory: `python -c "import x; print(x.__file__)"`, `node_modules/<pkg>`, `go doc`, `go env GOMODCACHE`, `bundle exec gem contents`.

**Fix**
- Use the real API (B). The code was broken or behaved differently, so fixing it changes behavior.
- Report as N if the intended call is unclear.

### TEST — Test slop

**Looks like**
- Tests that assert the mock was called with what the test told it.
- Tests that mock the unit under test.
- Tests with no assertions, or only `is not None` or `toBeDefined` assertions.
- Assertions copied from the current output, not from the requirement.
- `try/except` in a test that swallows the failure.
- `skip` or `xfail` added without a reason.
- Many copy-pasted tests that differ by one value, in a codebase that parametrizes.
- `test_function_works` names.
- Sleeps.
- Tests of private helpers instead of behavior.
- Fixtures that rebuild what a shared fixture provides.

**Signals**
- `rg -n 'assert_called|toHaveBeenCalled|\.called\b|mock\.|Mock\(|patch\('` in tests: compare the mock setup with the asserts.
- `rg -n '@pytest\.mark\.(skip|xfail)|\.skip\(|it\.skip|t\.Skip'`
- Test functions with no assert lines.

**Not slop when**
- Checking the interaction with a mocked external system is the point, such as "sends exactly one email".
- Snapshot tests are the convention and the snapshot was reviewed.

**Fix**
- Parametrize the duplicates, rename, and reuse fixtures (P). The tests run the same cases.
- Strengthen an assertion, remove a self-mock, or remove a swallowing `try` (B). The test may now fail and expose a real bug. Report that, and don't weaken the test back.
- Delete a test that tests nothing (B).

### NAME — Generic and inflated names

**Looks like**
- `data`, `result`, `res`, `info`, `item`, `obj`, `temp`, `val`, `handle`, `process`, `manager`, `helper`, `utils`, `do_stuff`, `my_*`, used where a domain word exists.
- Overlong names that encode types or the whole sentence, like `user_data_dictionary_list`.
- `new_`, `updated_`, `improved_`, `enhanced_`, `final_`, `v2` prefixes.
- Names that differ from the codebase's word for the same thing.
- Boolean names that don't read as yes/no.

**Not slop when**
- The scope is tiny and the meaning is obvious, like `i` in a short loop.
- The name matches an external API's field.

**Fix**
- Rename a local or private name (S, or P if it is used across files).
- Rename a public name (B).

### VERB — Verbose code

**Looks like**
- `if cond: return True else: return False`.
- `== True` and `!= False`.
- `else` after `return`.
- Deep nesting where guard clauses fit the codebase.
- Intermediate variables used once that add no name value.
- Conversions that do nothing, like `str(s)` on a string or `list(xs)` on a list.
- `async` functions that await nothing.
- f-strings with no placeholders.
- Manual loops where the codebase uses a comprehension or a library call.
- Manual index loops.
- Building a list only to check whether it's empty.
- `len(x) == 0` where the codebase writes `not x`.
- Redundant `return None`.

**Not slop when**
- The longer form is the codebase's style.
- The intermediate variable names a concept.
- The shortening would change evaluation order or laziness.

**Fix**
- Simplify (S for purely syntactic rewrites, P otherwise).

### LOG — Log and output noise

**Looks like**
- A log line at the entry and exit of every function.
- `info` for debug detail.
- Logs in tight loops.
- Emoji or decoration in logs.
- Log-and-rethrow at each layer.
- `print` mixed with the logger.
- Messages without the identifiers needed to debug.
- Secrets, tokens or personal data in logs.
- A second logger set up next to the codebase's one.

**Signals**
- `rg -n 'log(ger)?\.(info|debug|warn|error)|logging\.|console\.(log|info|warn|error)'`, compared with the baseline's levels.
- Log density per function.

**Not slop when**
- It's an audit record the codebase requires.
- Entry and exit logs are the convention for this layer.

**Fix**
- Drop the noise or move it to the right level (P). Observable output changes, but not program behavior. Group these in their own batch so the user can approve them together.
- A secret in a log: 🔴 and B, put first in the plan.

### DRIFT — Drift from the codebase's conventions

**Looks like** code that works but doesn't look like the rest:
- a different error style
- a different logging library or format
- a different HTTP client
- a new config loader
- a different test framework style
- a different file layout
- dataclasses where the codebase uses pydantic, or the other way round
- callbacks where the codebase uses async/await
- a different naming case

**Signals** Compare each new construct with the baseline's conventions.

**Not slop when** The change is a deliberate migration, stated in the commit or PR, or the codebase is mixed with no majority.

**Fix**
- Rewrite to the convention: P when the semantics are identical, B otherwise.
- A large rewrite: N, as a recommendation.

### BLOAT — Structural bloat

**Looks like**
- Functions much longer than the baseline that do several things.
- A module of thin pass-through functions.
- Code split into many micro-files or classes with one method each.
- Parameters threaded through layers that don't use them.
- Overlong docstrings.
- Configuration for things that never vary.

**Not slop when** Size matches the codebase, or the length is one irreducible sequence.

**Fix**
- Extract or merge only when it clearly reads better and matches the codebase (P).
- Otherwise N. Splitting a function to satisfy a number is churn.

**Output contract for `3-findings.md`** (or `3-findings-<group>.md`):

```
FILES: <every file owned, one per line>

FAMILY PASSES
| File | CMT | DEF | ERR | SPEC | DUP | DEAD | FAKE | API | TEST | NAME | VERB | LOG | DRIFT | BLOAT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <path> | 3 | 0 | 1 | – | … |
(a count per family; "–" only for a family not in scope via --families)

FINDINGS
### <ID: FAMILY-n, e.g. ERR-2> <one-line claim>
- Where: <path:line-line>
- What: <the slop, quoted briefly>
- Evidence: <why it is slop here: baseline convention, callers, the reuse-index entry, tool output>
- Not slop because?: <the "not slop when" cases checked and why they don't apply>
- Fix: <the change, concretely> · Class: S | P | B | N · Severity: 🔴 | 🟠 | 🟡
- After: <the code after the fix, for P and B; omit for deletions>

OUT OF SCOPE: <n> similar findings in older code, by family (counted, not listed)
```

---

## Part 3 — Verifying findings

Try to disprove each finding before it is kept. The check depends on the family:

| Family | Disprove it by |
|---|---|
| CMT | Reading the comment against the code and the git blame. Does it carry a why that the code doesn't show? Is the codebase's density actually lower? |
| DEF | Tracing the value back to its source: types, validators, constructors, every caller. A check that can fire for any real input isn't overkill. Its removal is B, or it isn't a finding at all. |
| ERR | Finding the boundary handler and confirming the error would reach it and be logged once. Checking whether the swallowing is documented best-effort behavior. |
| SPEC | Counting implementations and users across the whole repository, including tests and other packages in a monorepo, and searching for plans that mention a second one. |
| DUP | Reading the existing helper and comparing behavior on edge cases: empty, None, time zones, errors, ordering. Different behavior makes the fix B or drops the finding. |
| DEAD | Searching the whole repository for the name as text, not only as a symbol, to catch strings, configs, templates, reflection, `__all__`, entry points and public exports. |
| FAKE | Checking whether the code is reached in production paths and whether the change presents it as complete. |
| API | Reading the installed library source or running the type-checker. Never decide from memory. |
| TEST | Running the test after mentally breaking the code. Would it fail? If it can still fail for a real bug, it's not slop. |
| NAME | Checking the codebase's word for the concept, and every use of the name. |
| VERB | Confirming the shorter form keeps evaluation order, laziness, types and exceptions. |
| LOG | Checking what middleware and callers already log, and the codebase's level conventions. |
| DRIFT | Confirming there is a majority convention, with examples, and that the change doesn't state a deliberate migration. |
| BLOAT | Checking the baseline sizes, and whether the proposed split actually reads better. |

**Output contract for `4-verification.md`:**

```
| In | Claim | Checked how | Result | Class | Severity |
|---|---|---|---|---|---|
| ERR-2 | <claim> | boundary at <path:line> logs and returns 500; traced caller <path:line> | Confirmed | B | 🔴 |
| DEAD-4 | <claim> | name found in <config path> | Dropped: used by config | — | — |

MERGED: <which into which, or none>
SKEPTICS: <ID → verdict, or "inline mode, none run">
RECLASSIFIED: <ID: old → new class and why, or none>
```
