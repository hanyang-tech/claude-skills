# Review lenses

How to review one unit of a change. Part 1 is done once per review. Parts 2 to 4 are done for every unit: first the branch inventory, then the five lenses, then deciding what is a finding. Part 5 is the shape of what you write.

The inventory comes first because judging as you list is how branches go missing: the branch that looks fine is never written down, and the one next to it that isn't fine is never looked at. The lenses are separate passes for a similar reason. Reading the same code five times, each time asking one kind of question, finds what one pass asking everything at once walks past. A pass for bugs reads with concrete values, a pass for readability reads as a newcomer would, and a pass for logging reads as the person on call at 3 a.m. with nothing but the logs.

---

## Part 1 — The codebase's way

Readability, cleanliness and logging are judged against how this codebase already does things, not against your preferences. Find that out before reviewing any unit.

1. **Written rules.** Look for `CONTRIBUTING.md`, a style guide, `CLAUDE.md` or `AGENTS.md`, `docs/patterns.md` or similar, a logging or observability guide, and the formatter and linter config (`pyproject.toml`, `.eslintrc*`, `.editorconfig`, `rustfmt.toml`, …). Note what they say that bears on the change.
2. **Examples.** For each kind of thing the change adds (a handler, a component, a test, a migration, a CLI command), open at least two existing ones of the same kind, near the change when possible. Note how they name things, handle errors, validate input, structure the file and test.
3. **Logging.** Find out how the codebase logs:
   - the logger it uses and how a module gets one (`logging.getLogger(__name__)`, an injected logger, `slog`, `pino`, …), and whether it logs structured fields or formatted strings
   - how it attaches context: request or correlation IDs, user and entity IDs, and the field names it uses for them
   - how it logs exceptions (with the stack trace, and how)
   - what it logs at each level, from at least two examples of each level in use
   - whether it has a separate audit mechanism (an audit table, an event stream, an `audit_log()` helper) that audit-relevant actions should go through instead of, or as well as, the ordinary log
   - what it must never log: a redaction helper, a list of sensitive fields, or a written policy
4. **Conventions.** Write down only what is written as a rule or what the examples show at least twice. Where the examples disagree with each other, the convention is mixed and nothing is held against the change on that point.

---

## Part 2 — The branch inventory

Before applying any lens, list every branch in the unit's changed code. A branch is any point where execution can go more than one way:

| Kind | Branches to list |
|---|---|
| Conditionals | Each `if`, `elif` / `else if` and `else`, including the **implicit `else`** when there is none: what happens when no condition matches? |
| Multi-way | Each `match`, `switch` or `case` arm, the default arm, and fall-through. Is every value of the enum or union handled? |
| Early exits | Each `return`, `break`, `continue` and guard clause that leaves before the end. |
| Loops | Zero iterations, one, many; the exit condition; an exit from the middle. |
| Errors | Each `throw` or `raise`; each `catch` or `except` and what it catches; what happens to an error that no handler catches; `finally`. |
| Short-circuits | `&&`, `\|\|`, `and`, `or`, `??`, `?.` and ternaries, where the side that doesn't run matters. |
| Defaults | Default arguments, `get(key, default)`, `or default`, fallback values: the path where the default is used. |
| Async | A promise or future that rejects; a timeout; a cancellation. |
| Removed | Every branch the **base version** had that the change removed or merged. What handles that case now? |

For each branch, write a row:

- **Condition:** when it is taken, in words.
- **Input:** a concrete input or state that takes it. If you can't find one, the branch may be dead: say so, since that is a cleanliness finding.
- **What happens:** traced, not assumed.
- **Handled:** ✅ correct · ❌ wrong (a finding) · ❓ depends on intent (a question).
- **Tested:** the test that reaches it, `no`, or `unknown`. Use a branch coverage report when one was run.
- **Logged:** the level and message it logs, or `—`. This column feeds the logging lens.

List every branch before judging any of them. Then the lenses work from the rows.

For a mechanical unit, the inventory is empty, with how it was confirmed mechanical. For a very large unit, split the inventory by function, but every function in the unit has one.

---

## Part 3 — The five lenses

Read the unit once per lens. Count what each lens checked, even when it finds nothing; "0 findings" means nothing without what was looked at.

### Bugs — does the code do what it evidently means to do?

Follow the inventory's inputs through the changed lines, one row at a time, and add a normal input and two awkward ones of your own.

- **Boundaries:** empty, one element, the maximum, zero, negative; off-by-one; inclusive vs. exclusive ranges; the first and last iteration.
- **Missing values:** `None`, `null`, `undefined`, optional fields, missing keys, empty string vs. absent.
- **Types and conversions:** integer division, floats for money, string vs. number comparison, timezone-naive vs. aware datetimes, encoding, precision lost in a cast.
- **Error paths:** exceptions swallowed or caught too broadly; an error returned and ignored; partial failure leaving half-written state; cleanup outside `finally` or its equivalent; a retry around something that isn't idempotent.
- **Resources:** files, connections or locks not released on every branch; missing timeouts; unbounded growth of a list, cache or queue.
- **State and concurrency:** shared mutable state; check-then-act races; async calls not awaited; an ordering that isn't guaranteed; a cache that isn't invalidated.
- **Copy and paste:** a repeated block with one name not changed; the wrong variable used.
- **Changed contracts:** callers not updated for a new signature, return value, default or meaning. Compare with the base version and open every caller.
- **Security basics:** input reaching a query, shell, path, template or redirect unescaped; a new route or action without the authorization check its neighbors have.

### Logic — is the reasoning behind the code right?

The code can do exactly what it was written to do and still be wrong, because what it was written to do is wrong or incomplete. Read the inventory as a whole.

- **Purpose:** trace the main scenario from `2-summary.md` end to end. Does the change achieve it?
- **Completeness of the decisions:** taken together, do the branches cover every input the domain allows? Which input falls through to the implicit `else` or the default arm, and is that what should happen to it?
- **Consistency of the decisions:** overlapping or contradictory conditions; an early return that shadows a later check; checks whose order matters; two branches that should behave the same and don't.
- **Removed branches:** for each row marked removed, is the case still handled somewhere, or was it lost?
- **The rule's place:** validation in one caller but not the others; a business rule written in two places that will drift; logic in a layer that can be bypassed.
- **Invariants:** what must always hold (a balance never negative, a list kept sorted, a key unique)? Does every branch keep it, including the error branches?
- **Data flow:** a value computed and not used, used before it is set, overwritten, or read stale after a write.
- **Fit to the data:** quadratic work on a list that grows; a query per item in a loop; loading every row to count them.
- **Tests that test the logic:** which branches no test reaches, and of those, which carry risk (errors, money, permissions, data changes); assertions that can't fail; mocks that restate the implementation.

### Readability — how quickly does a new reader understand it correctly?

Read the unit as someone who has never seen it. Where do you have to stop and work something out?

- **Names:** say what a thing is or does, not how; one name per concept across the change; no misleading names (a `get_` that writes, a `count` that is a list); booleans that read as questions.
- **Size and levels:** a function doing several things; high-level steps mixed with low-level detail. More than about 40 lines or 3 levels of nesting is a signal to look, not a rule.
- **Control flow:** deep nesting where guard clauses would read straight; exceptions or flags used to steer ordinary flow; boolean arguments that make call sites unreadable (`send(msg, True, False)`). A branch inventory that was hard to write is often a readability finding in itself.
- **Unnamed values:** magic numbers and strings; a complex condition that a named variable or function would explain.
- **Comments:** say why, not what. A comment that disagrees with the code is worse than none, and may be a bug: check which one is right.
- **Signatures and types:** return types and optional values made explicit where the language allows; parameters in an order a caller can follow.
- **Locality:** one behavior spread across many files or far-apart lines, so a reader has to jump to follow it.

### Cleanliness — what does the change leave behind, and does it sit well in the codebase?

- **Dead code:** unused functions, parameters, imports, variables; branches no input can take (from the inventory); a flag that is always on.
- **Leftovers:** debug `print`, `console.log`, `breakpoint()`, and temporary log lines; commented-out code; `TODO` or `FIXME` without a ticket; `.only` or `.skip` in tests; temporary files.
- **Duplication:** new code that repeats an existing helper (search the codebase for it) or repeats itself within the change.
- **Conventions:** departures from the conventions in Part 1: error handling, validation, structure, file placement, naming.
- **Scope:** unrelated changes mixed in (a drive-by refactor, formatting churn across a whole file) that make the change harder to review; a commit message that doesn't describe its commit; one commit mixing unrelated work.
- **Over-engineering:** an abstraction with one implementation; configuration for a value that never changes; generality nobody uses yet.
- **Noise:** defensive checks that can't trigger; catch-log-rethrow layers; wrappers that add nothing.
- **Tools:** the formatter's and linter's result, run or read from CI.

### Logging — could someone audit this, and debug it, from the logs alone?

Work from the inventory's `Logged` column. Read as the person who has to answer, weeks later, either "who did this, and when?" or "why did this fail for this customer?", with nothing but the logs.

**Levels.** Each message at the level that matches what happened, in the codebase's own usage where Part 1 found one:

| Level | For | Examples |
|---|---|---|
| `ERROR` | An operation failed and someone may need to act. | A payment call failed after its retries; a write was rolled back; an invariant was violated. |
| `WARN` | Something unexpected that was handled, or a degraded result. | A retry; a fallback or default used; input rejected in a way that suggests a misbehaving client; a deprecated path used; a limit nearly reached. |
| `INFO` | A significant event in the normal flow, and every audit-relevant action. | An order created; a job finished with its counts; a user's role changed; a config reloaded. |
| `DEBUG` | Detail a developer needs to understand a decision. | Which branch was taken and why; intermediate values; the result of a lookup. |
| `TRACE` | Very fine detail, normally off. | Function entry and exit; payloads; each loop iteration. |

Common level mistakes: an expected, handled condition (a user not found, a validation error returned to the client) logged at `ERROR`, which buries real failures and pages people for nothing; a real failure logged at `DEBUG` or `INFO`, so it is invisible in production; per-item `INFO` inside a loop that runs thousands of times.

**Coverage of the branches.** Go down the inventory:

- **Every failure branch leaves a trace.** A `catch` that handles an error and carries on logs it at `WARN` or `ERROR`. A swallowed error with no log, or with only a `DEBUG` log, is a finding.
- **Each error is logged once.** Log it where it is handled, or attach context and rethrow, but not both at every layer. The same stack trace three times makes the logs harder to read, not easier.
- **Fallbacks and defaults** that hide a problem (a missing config value, a cache miss falling through to a slow path, a default currency) log at `WARN`, or `DEBUG` when they are routine.
- **Decisions that will be questioned later** (why a request was rejected, why a discount wasn't applied, why a job skipped a record) can be reconstructed from a `DEBUG` or `INFO` line.

**The audit trail.** An audit-relevant action leaves a record of **who** (the actor: user, service or job), **what** (the action), **which** (the entity and its ID), **the outcome** (success or failure, and why), **when** (usually added by the logger), and **the correlation or request ID**. Audit-relevant actions include:

- creating, changing or deleting records that matter to the business or the user
- authentication and authorization events: sign-in, sign-out, failed sign-in, permission denied, a role or permission changed
- money moving, and anything with a legal or compliance trail
- admin and support actions, configuration changes, feature flags flipped
- data exports and bulk operations

Both outcomes count: a permission denied is as audit-relevant as a permission granted. Where Part 1 found a separate audit mechanism, the action should go through it; a plain log line instead is a finding.

**Content.**

- **Context:** the IDs needed to find the related lines (request, user, entity) in the codebase's field names, as structured fields when the codebase uses them.
- **Exceptions with their stack trace,** the way the codebase does it (`logger.exception(...)`, `exc_info=True`, passing the error object rather than `String(err)` or `str(e)`).
- **Messages that can be searched:** a fixed message with variable data in fields, not values interpolated into the middle of a sentence, where the codebase logs structured data.
- **Enough to act on:** "failed" alone isn't; "charge failed for order 123: card_declined after 3 attempts" is.

**What must not be logged:**

- secrets: passwords, tokens, API keys, session cookies, private keys, connection strings with credentials
- full card numbers, bank account numbers, government IDs
- personal data beyond what the project's policy allows; check Part 1 for a redaction helper and use it
- whole request or response bodies at `INFO` or above; they carry all of the above sooner or later

**Mechanics.**

- The project's logger, not `print` or `console.log`.
- Lazy formatting for messages below the usual production level (`logger.debug("x=%s", x)`, not an f-string), and no expensive work just to build a `DEBUG` message unless it is guarded.
- No log line that can run unbounded times at `INFO` or above without rate limiting or aggregation.

Not every branch needs a log line. A branch whose outcome is already visible elsewhere (an HTTP response the framework logs, an exception that propagates to a handler that logs it) is covered. The finding is a failure or an audit-relevant action that leaves no trace, a log at the wrong level, or a log that leaks or can't be used.

---

## Part 4 — What makes a finding

Each kind needs its own evidence. Without it, drop the finding or turn it into a question.

| Lens | The finding has to show |
|---|---|
| Bug | The concrete input or state, what happens (traced or reproduced), and what should happen. |
| Logic | The scenario where the reasoning fails, the input that falls through the decisions, or both places that can drift, with `path:line` for each. |
| Readability | The current code, a rewritten version, and which question a reader can now answer faster. If you can't write a clearly better version, it isn't a finding. |
| Cleanliness | The exact location. For duplication, the existing helper's location. For a convention, the written rule or two locations that establish it. For dead code, why no input reaches it. |
| Logging | The branch or action (its inventory row), what is logged now, and the log line it should have: level, message and fields, in the codebase's logging style. For a leak, the field that leaks and how to redact it. |

Not findings:

- **Taste.** A preference the codebase doesn't share.
- **Problems in code the change doesn't touch,** unless the change makes them worse or newly reachable. Mention them under `NOTICED NEARBY` at most.
- **What the formatter or linter would fix,** when the project runs them in CI. Report the tool's result once instead.
- **A log line the framework already writes,** or one for a branch whose outcome is visible elsewhere.

Propose a rating for each finding (Step 5 settles it):

- Bugs and logic flaws can be anything from 🔴 to 🟡, by impact and how likely the scenario is.
- Readability and cleanliness are 🟡 by default. They are 🟠 when they mislead (a name or comment that says the wrong thing), hide a bug, or break a written rule. A leftover that changes behavior, such as a `.only` that disables the rest of a test suite, is a bug and rated as one.
- Logging is 🟡 for a level, field or wording problem. It is 🟠 for a failure branch that leaves no trace, an audit-relevant action that isn't recorded, an expected condition logged at `ERROR` on a busy path, or personal data logged against policy. It is 🔴 for secrets or credentials written to a log.
- An untested branch is a finding only when it carries risk (an error path, money, permissions, data changes); it goes under logic. Other untested branches stay in the inventory, where the user sees them.
- Anything that depends on intent the code can't show is a 💬 question.

---

## Part 5 — Output contract

Write the conventions block once, then one section per unit. Every section, every inventory column and every lens line appears; where there is nothing, write `none` and what was checked.

````
## CODEBASE
Written rules: <file — what it says that matters here>, or none found (looked in: …)
Examples opened: <kind: path, path>
Conventions:
- <convention> — <rule, or two locations>
Logging: logger <how obtained> · <structured | formatted> · context fields <names> · exceptions <how> · levels <what each is used for, with locations> · audit <mechanism, or "none: plain INFO logs"> · never logged <policy or helper, or "none found">
Mixed: <conventions the examples disagree on, or none>

## U<n> <what it changes> · <rank>
READ: <functions read whole> · base version read: <yes | no, why> · callers: <path:line, …> · tests: <paths | none> · coverage report: <run | not run: why>

BRANCHES
| # | Where | Condition | Input that takes it | What happens | Handled | Tested | Logged |
|---|---|---|---|---|---|---|---|
| b1 | `path:42` | amount ≤ 0 | amount = 0 | raises ValueError | ✅ | `test_zero_amount` | — (propagates to handler, which logs) |
| b2 | `path:47` | implicit else: currency not in RATES | currency = "JPY" | KeyError, 500 | ❌ → U<n>-B1 | no | — |
| b3 | `path:55` | except TimeoutError | gateway slow | returns None, carries on | ❌ → U<n>-G1 | no | — |
| r1 | base `path:60` | removed: retry on 503 | gateway 503 | now fails at once | ❓ → question | — | — |
Totals: <n> branches · <n> removed · ✅ <n> · ❌ <n> · ❓ <n> · tested <n> · untested <n> · unknown <n> · logged <n>

LENSES
- Bugs: <n> · checked: <rows followed, plus the extra inputs tried>
- Logic: <n> · checked: <completeness of decisions, removed branches, invariants, risky untested branches>
- Readability: <n> · checked: <what was read as a newcomer>
- Cleanliness: <n> · checked: <leftovers searched, helpers searched for, conventions compared, tools>
- Logging: <n> · checked: <failure branches <n>, logged <n> · audit-relevant actions <n>, recorded <n> · levels · sensitive fields>

FINDINGS
- [U<n>-B1] <claim> — `path:line` · branch b2 · proposed 🔴
  Input or state: … · What happens: … · Expected: … · Suggested fix: …
- [U<n>-L1] <claim> — `path:line` · proposed 🟠
  Scenario: … · Suggested fix: …
- [U<n>-R1] <claim> — `path:line` · proposed 🟡
  Now:
  ```<lang>
  …
  ```
  Clearer:
  ```<lang>
  …
  ```
  Why: <the question a reader can now answer faster>
- [U<n>-C1] <claim> — `path:line` · proposed 🟡
  Evidence: <the leftover, the existing helper's location, or the rule or two locations>
- [U<n>-G1] <claim> — `path:line` · branch b3 · proposed 🟠
  Logged now: <nothing | the current line> · Should log:
  ```<lang>
  logger.warning("payment gateway timed out", extra={"order_id": order.id, "attempt": attempt})
  ```
  Why: <what someone couldn't audit or debug without it>

CHECKED AND SOUND: <what was examined and found right, per lens>
QUESTIONS: <what depends on the author's intent>
NOTICED NEARBY: <problems in untouched code, or none>
````

For a mechanical unit, `READ` says how it was confirmed mechanical (`--color-moved`, uses of the renamed symbol read), `BRANCHES` says `none: mechanical`, and the bugs, logic and logging lines say `mechanical: <how confirmed>`.
