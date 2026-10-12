# Finding a simpler implementation

The goal is to answer one question: could this change produce the same behavior with less?

**Simpler means fewer things to understand**: fewer concepts, states, branches, files, layers or dependencies, for the same behavior. It doesn't mean fewer characters. Code that is shorter but denser or cleverer is not simpler, and neither is code that drops a case the original handled.

## 1. Start from the behavior, not the code

Reading an implementation first makes it look inevitable. So before studying how the PR does it:

1. Take the behavior changes from the change summary.
2. Look at the codebase around the change: what already exists that is close to this (helpers, a similar feature, the framework's own facilities). If you were given a conventions list, your sketch follows it.
3. Sketch, in a few lines, the least code that would produce those behaviors here. Write the sketch down before going further: it is the first section of the output, and a sketch made after studying the PR is just the PR again.

Then compare the sketch with the PR. Each difference is one of two things:

- **A case your sketch forgot.** The PR was right to handle it. Good: note the case, and move on.
- **Something the PR didn't need.** That is a candidate.

## 2. Where to look

From the largest win to the smallest. Stop going down the list for a piece of code once a larger simplification would remove it anyway.

Go through all ten for the change as a whole, and record a line for each under `LOOKED AT`: what you searched or compared, and what came of it. "Nothing found" is a result. A kind with no line was not looked at.

1. **A different approach.** Is there a design that makes most of this change unnecessary? Doing the work in the query and not in a loop, using a constraint and not a check, deriving a value and not syncing it, configuring an existing component and not writing a new one.
2. **It already exists.** Search the repository for a helper, base class or utility that does this, and check the standard library, the framework and the dependencies already installed. Code that reimplements something available is the most common simplification, and the easiest to prove.
3. **A better place for the change.** The same fix made at the source and not in each caller. One change in a shared function and not five in its users. A new parameter on an existing path and not a parallel path.
4. **Generality nobody uses.** An interface with one implementation. Options that no caller passes. A setting for a value that never varies. A plugin point with one plugin. Check the call sites: if there is no second user in the PR or the repository, it is speculation.
5. **State that needn't exist.** A stored value that could be computed from what is already there. A flag that mirrors another field. A cache with no measured need. Each piece of stored state is something that can go out of date.
6. **Special cases that a general rule covers.** A separate branch for the empty list when the loop already does nothing. Three near-identical branches that differ by one value. Handling for one type that the generic path already gets right.
7. **Dead weight.** Unused parameters, fields and imports. Branches that can't be reached. Defensive checks for something the caller or the type already guarantees (cite the guarantee). Compatibility code for callers that no longer exist. Leftover debugging.
8. **Duplication.** The same logic twice within the PR, or a copy of something that already exists elsewhere. Suggest sharing only when the copies must change together. Two things that merely look alike today are better left apart.
9. **Data shape.** A different structure that makes the logic trivial: a map and not a nested search, one status value and not three booleans, a sorted list and not repeated scans.
10. **Local control flow.** Early returns in place of deep nesting, a built-in in place of a hand-written loop. Only when it removes something to think about. This is the level where taste starts, so keep the bar high.

## 3. What each suggestion needs

- **The simpler version, shown.** A sketch of the code, or a description exact enough that the author could write it without guessing.
- **What it removes.** Lines, files, a class, a concept, a dependency, a state.
- **Its behavior.** Go through the cases the current code handles (use the case inventory if you were given one; otherwise list the cases the code and its tests cover) and confirm the simpler version handles each. If behavior would differ, say exactly how, and why that is acceptable or what it costs.
- **It fits the codebase.** The simpler version does things the way this project does them (the conventions list, if you were given one, or the surrounding code). A version that is shorter because it skips the project's service layer or its shared helper is a departure, not a simplification.
- **Evidence.** The search that shows no other user of the thing removed. The callers you read. Where running code is allowed, the simpler version applied in the scratch worktree with the PR's tests passing against it. Say which of these you did.
- **Why it might be the way it is.** Think of the reason the author could have had: a requirement that is coming, a constraint elsewhere, a performance need, a convention in this codebase. If you find the reason and it holds, drop the suggestion. If a reason is plausible but you can't confirm it, make it a question and not a finding.

Rate the size:

- **large:** a different approach, or a component, file or layer that can go
- **small:** within a function

## 4. What not to report

- Naming, formatting and style, which are the linter's job.
- A preference between two constructs that are equally simple.
- A change that would make this code inconsistent with how the surrounding code does the same thing.
- Rewrites of code the PR didn't touch.
- Micro-optimizations.
- "Simplifications" that only move the complexity somewhere else.

If the change is already about as simple as it can be, say so and say what you compared it with. That is a useful result.

## Output contract

Every section appears, in this order. A section with nothing to list says `none` and why.

```
SKETCH
<the least code that would produce the behavior changes here, written before studying the PR's version>
Differences from the PR:
- <difference> → a case the sketch forgot: <case> | something the PR didn't need: [S<n>]

LOOKED AT
1. A different approach: <what was considered> → <[S<n>] | nothing found | covered by [S<n>]>
2. It already exists: <the searches run, the libraries checked> → <…>
3. A better place: <…> → <…>
4. Generality nobody uses: <call sites checked> → <…>
5. State that needn't exist: <…> → <…>
6. Special cases: <…> → <…>
7. Dead weight: <…> → <…>
8. Duplication: <…> → <…>
9. Data shape: <…> → <…>
10. Local control flow: <…> → <…>

SIMPLIFICATIONS
- [S1] <what can go> — path:line
  Kind: <which of the ten above>
  Now: <what the PR does, one or two lines>
  Simpler: <code sketch or exact description>
  Removes: <lines, files, concepts>
  Behavior: same | differs: <how>
  Cases checked: <which cases, and the result for each>
  Evidence: <search, callers read, tests run with their result>
  Why it may be this way: <a plausible reason, or "none found">
  Size: large | small
  Confidence: high | medium | low

QUESTIONS
- <where a simpler version exists but an unseen constraint might explain the current one>

ALREADY SIMPLE
- <parts examined where no simpler version was found, and what they were compared with>
```
