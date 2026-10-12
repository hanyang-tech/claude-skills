# Finding uncovered cases

The goal is a **case inventory** for the change, and from it the cases the implementation doesn't handle.

Work in this order: enumerate first, judge second. If you judge as you go, you stop listing the moment the code "looks fine", and the cases you never wrote down are the ones nobody checks.

## 1. Pick the units

One unit per behavior change in the change summary, plus any changed function that holds logic of its own. Skip pure moves and renames once you have confirmed they are pure.

## 2. Enumerate the cases

For each unit, go through every source below and write down the cases it gives. A case is a specific input or situation: "the list is empty", "the second call arrives before the first finishes", "the order was created before this field existed".

There are eight sources, and each unit is taken through all eight. Record which source each case came from. A source that gives nothing for a unit gets a reason ("dependencies: the function calls nothing outside the module"), so that an empty source can be told apart from a skipped one.

**The code's own structure.** The implementation tells you which cases its author saw, and where the rest fall.

- Every `if` without an `else`, every `switch` or match without a default, every chain of `elif`: what happens to a value that matches none of them?
- Every comparison (`<`, `<=`, `==`, a length or range check): the value exactly at the boundary, and one either side.
- Every early return, `continue`, `break` and raised error: is everything after it safe to skip (cleanup, a state update, a log, releasing a lock)?
- Every loop: zero iterations, one, many, and stopping partway with some effects already applied.
- Every default value and fallback (`x or default`, `??`, `.get(key, default)`): can the real value legitimately be the thing that triggers the fallback (`0`, `""`, `false`)?
- Every lookup, parse and cast: the key that is absent, the text that doesn't parse, the value of another type.

**What the old code did.** Read the removed lines and the base version of each changed function. A deleted branch, check or `catch` is a case the old code handled. Does the new code still handle it, or is it now someone else's job, and whose?

**Input values.** For each parameter, field and item of external data the change reads:

- Absent, `null`, empty, whitespace only.
- For collections: empty, one item, many, duplicates, unsorted where order is assumed, far larger than usual.
- For numbers: zero, negative, the limits, a fraction where a whole number is expected, values at each threshold the code uses.
- For text: very long, non-ASCII, mixed case, leading and trailing spaces, characters that mean something to whatever consumes it (a path, a query, a pattern, HTML).
- For dates and times: timezone boundaries, daylight-saving changes, the end of a month or year, far past and far future.
- A value equal to a sentinel or default the code uses to mean "not set".

**State.** What can the data look like when this code runs?

- First time ever, with nothing there yet. And again, with the result of the last run already there.
- The record doesn't exist, was deleted, is archived or disabled, or belongs to someone else.
- Data written before this change: a new field missing, an old format, an old enum value.
- A previous attempt that stopped halfway.
- Each role, permission level, tenant or plan that can reach this code.
- A feature flag or config value on, off, and missing.

**Callers and entry points.** Find every call site of the changed code and every route into it (a request, a background job, a CLI, a migration, a test helper). What does each one actually pass? A function that is correct for the caller the author had in mind is often wrong for another one.

**Dependencies.** For each call to a database, a network service, the file system, a queue or another module: it fails, times out, returns nothing, returns part of the result, returns more than expected, or succeeds after the caller gave up.

**Time and order.** The same call made twice. Two calls at once on the same data. Steps arriving out of order. A retry after a partial success. State changing between a check and the action that relies on it. The process stopping between two writes.

**Combinations.** Not all of them. Pick pairs that interact: an empty result together with pagination, a retry together with a non-idempotent write, an old record together with a new required field.

## 3. Trace each case

Follow each case through the code, including the unchanged code around the change, and give it a status:

| Status | Record |
|---|---|
| **Handled** | Where: `path:line`. |
| **Handled elsewhere** | By what: validation upstream, a type, a database constraint, the framework, or a shared helper the project routes this through. Cite it. Don't assume it. |
| **Can't occur** | Why, with the code that guarantees it. |
| **Not handled** | What actually happens, step by step: the value returned, the error raised, the state left behind. |
| **Unclear** | What it depends on. This becomes a question. |

For each case also note whether a test exercises it, and which test.

Trace with real values. "This might fail on empty input" is a guess. "With `items = []`, line 42 computes `total / len(items)` and raises `ZeroDivisionError`, which the handler at line 80 turns into a 500" is a finding.

## 4. Decide what is a finding

A case that is **not handled** is a finding when what happens is harmful:

- a wrong result, shown or stored
- data lost, duplicated, or left half-written
- a crash or an unhelpful error for input that can really occur
- a silent skip, where the caller believes the work was done
- access to something the caller shouldn't reach

It is not a finding when the outcome is acceptable: a clear error for input that can never be valid, or a case that truly can't occur. Say so under Checked and sound.

Rate each finding:

- **must fix:** a realistic input or state, and a serious outcome
- **should fix:** a less common path, or a milder outcome
- **consider:** narrow and low impact

For each finding give the smallest fix that covers the case. If several findings share a cause, say so: one change at the cause is better than a patch per symptom.

A case that is handled but not tested is a **test gap**, not a finding. List it only when the logic is risky or easy to break.

## Output contract

Every section appears, in this order. A section with nothing to list says `none` and why.

```
CASE INVENTORY
| # | Unit | Source | Case | Status | Where, or what happens | Tested |
|---|---|---|---|---|---|---|

Source is one of: structure, old code, inputs, state, callers, dependencies, time, combinations.
Every row has a status. A case that was listed and not traced is not finished.

SOURCES
| Unit | Structure | Old code | Inputs | State | Callers | Dependencies | Time | Combinations |
|---|---|---|---|---|---|---|---|---|
| <unit> | 6 | 2 | 9 | 4 | 3 | 0: calls nothing external | 2 | 2 |

Each cell is the number of cases that source gave for that unit, or 0 with the reason.

UNCOVERED CASES
- [C1] <the case> — path:line
  Input or state: <concrete>
  What happens: <traced, or reproduced with the command and output>
  Expected: <what should happen, or QUESTION if the code can't tell you>
  Severity: must fix | should fix | consider
  Confidence: high | medium | low
  Smallest fix: <change>

TEST GAPS
- <case> — handled at path:line, no test

QUESTIONS
- <what depends on the author's intent>

CHECKED AND SOUND
- <the cases that looked risky and turned out to be handled, with where>
```
