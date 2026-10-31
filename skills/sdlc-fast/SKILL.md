---
name: sdlc-fast
description: Faster variant of sdlc-loop. Runs the same iterative lifecycle with multiple agents (requirements → design → plan → build → review + test → integrate → retro, until every acceptance criterion is verified and the branch is release-ready), tuned for wall-clock time. Independent slices are built in parallel lanes in their own git worktrees. Verify runs targeted tests, and later rounds re-check only the fix. The full suite runs once per iteration, the tester adds only missing tests, flaky tests are timeboxed and quarantined, and MINOR findings go to the backlog instead of fix rounds. Small low-risk slices get one light verifier, only contract, data-model and trust-boundary changes go back to the architect and the user, and every phase is timed. Use when the user invokes /sdlc-fast, asks for a fast, quick or parallel SDLC or end-to-end build, or says sdlc-loop is too slow (options --spec, --max-iterations, --lanes, --verify, --auto, --dir, --patterns, --models).
---

# SDLC Fast

Take a piece of work from idea to release-ready by going round the lifecycle in iterations, like sdlc-loop, but spend the time where it buys quality. Each iteration delivers one or more thin, working slices, built side by side when they don't touch each other, and what they teach you changes the next iteration.

Work to deliver: `$ARGUMENTS` (if empty, use the task from the conversation; if there is none, ask for it).

You are the **driver**. Subagents can't spawn each other and can't talk to the user, so you run the loop, hold the gates, and move files between roles. This skill is self-contained: it doesn't need any other skill to be installed.

## Where the time goes, and what this skill does about it

Measured on real sdlc-loop runs, about half of the agent time went to engineers, a fifth each to testers and architects, and only a twentieth to reviewers. The waits came from serial slices, repeated fix rounds that redid the whole verify, full test suites run several times per iteration, flaky-test hunts, mid-iteration design changes waiting at a gate, and spare iterations spent on MINOR findings. Each rule below removes one of those without dropping a check:

| Time sink | Rule here |
|---|---|
| One slice at a time | [Lanes](#phase-3--plan-the-iteration-driver): independent slices are built and verified in parallel worktrees |
| Every fix round re-does the whole verify | [Delta rounds](#fix-rounds-are-delta-rounds): the reviewer reads only the fix diff, the tester re-runs only what failed or what the fix touched |
| The full suite runs in every round and again at integrate and release | [Targeted tests](#phase-5--verify) in verify; the full suite runs once per iteration, at Integrate, and Release reuses it when nothing changed |
| Testers writing hundreds of tests that repeat the engineer's | The tester reads existing tests first and adds only the missing cases |
| Flaky tests eating fix rounds | [Timeboxed and quarantined](#flaky-tests) |
| MINOR findings causing fix rounds and spare iterations | MINORs go to the backlog and `release.md`; they never start a round or an iteration on their own |
| Design deltas and the gates that wait on them | Only a change to a contract, the data model, a trust boundary or a dependency goes to the architect and the user; other lanes keep running while the user decides |
| A full reviewer and tester pair on a twenty-line slice | [Light verify](#light-verify): one verifier for small, low-risk slices |
| No way to tell what was slow | Every phase and agent is [timed](#timing) |

What does **not** change: the reviewer and tester stay independent of the engineer, every criterion still needs a passing test, the full suite and the scanners run before every commit lands on the branch, and Release still runs the final review, the security pass and the skeptics.

## Principles

- **Loop, not waterfall.** Requirements and design are revisited every iteration, so they only need to be good enough to build the next slices. The first working slice tells you more than another hour of planning.
- **Acceptance criteria are the exit condition.** The loop ends when every numbered criterion is verified, and every invariant covered, by a passing test or an explicit check. Without that list the loop has no principled way to stop, so nothing gets built until it exists.
- **State lives on disk.** Every phase writes to the work directory, and agents are handed file paths, not your summaries. This keeps each agent's context small, and it lets a run resume after a context summary or in a new session.
- **Independent roles.** The agent that wrote the code doesn't review or test it. The reviewer and tester get fresh context and never see the engineer's reasoning, so they judge the code against the criteria instead of against the author's story about it.
- **Run each check where it's cheapest to be complete.** Targeted tests while a slice is being fixed, the full suite once the slices are together, scanners at every integrate, a whole-branch review at release. A check run more often than that buys nothing; a check skipped lets a flaw get built on.
- **Spend rounds on what blocks.** A fix round is for BLOCKER and MAJOR findings and failing criteria. Everything else is recorded and scheduled, not fixed on the spot.
- **A failure goes back to its cause.** A failing test isn't always a code problem; it can be an ambiguous criterion or a design that can't work. Send each failure to the phase that owns the cause (see [Routing](#routing-failures-back)).
- **Relay faithfully.** Pass findings between agents verbatim. Don't soften, drop, or add to them, and never record a verdict an agent didn't give.

## The loop

```
        ┌────────────────── next iteration: criteria or backlog remain ───────────────────┐
        ▼                                                                                 │
  1 Requirements → 2 Design → 3 Plan ─┬─ lane a: 4 Build → 5 Verify ─┐                     │
                                      ├─ lane b: 4 Build → 5 Verify ─┼─ 6 Integrate → 7 Retro ┤
                                      └─ lane c: 4 Build → 5 Verify ─┘  (merge lanes,       │
                                                                         full suite once)  ▼
              a failure routes back to the phase that caused it            all criteria pass → Release
```

Phases 1 and 2 are **revisited, not redone**. From iteration 2 on, run them only if the previous retro queued something for them; otherwise note "no change" in the iteration file and go straight to Plan.

## Working method

A long run drifts. Phases get merged, a brief gets paraphrased from memory, an agent's half-answer gets finished by the driver. With lanes running side by side, drift is easier still. Five habits make a skipped step visible:

**1. Read the reference before the step that uses it.** The references are instructions, not background, and this file doesn't repeat them.

| Before | Read, in this run |
|---|---|
| Creating the work directory, and the first time you write each artifact | [references/templates.md](references/templates.md), the whole file |
| Launching a role, each iteration | That role's section of [references/roles.md](references/roles.md), and its row in the Contract check table there. The brief and the output contract go to the agent as written, with the placeholders filled in, not as you remember them |
| Planning slices, and checking a report's `PATTERNS` lines | The patterns file |
| Resuming, or carrying on after a context summary | `state.md`, the current iteration file and its lane files, then the rows above for the phase each lane is in. A summary doesn't carry the briefs or the templates |

The language references are for the agents. Your part is to check that each file exists and to hand over its absolute path.

**2. One task per phase, per lane.** At the start of each iteration, fill in the `Phases` checklist in the iteration file and the lane checklist in each lane file. If the session has a task list (TaskCreate or TodoWrite), create a task for each phase, and for Build and Verify one per lane, named like `It. 2b · 5 Verify`. The checklists are what survive a context summary.

**3. A phase is done when its output is on disk,** not when its agent returns:

| Phase | On disk before it is ticked |
|---|---|
| 1 Requirements | `requirements.md` updated and its gate recorded in `state.md`; or "no change" in the iteration file |
| 2 Design | `design.md` and the architect's report, or the driver's dated design note (see [Phase 2](#phase-2--design)); or "no change" |
| 3 Plan | The Lanes table in the iteration file, and a Plan section in each lane file |
| 4 Build (per lane) | The engineer's report, the Build section of the lane file, and the lane's round commit |
| 5 Verify (per lane) | A report from each verifying agent for every round, and a row per round in the lane's Verify section |
| 6 Integrate | Each lane's completeness table, the merged commits, the full-suite and scanner results in the Integrate section, and the criteria table in `state.md` |
| 7 Retro | The Retro section with its `DECISION`, and the Timing table filled in |

**4. Count before committing and before releasing.** Each lane has a completeness check before it is merged, and [Release](#release) has one for the whole branch. Numbers that don't match send you back to the phase that owes the work.

**5. Check every agent report against its contract,** and send an incomplete one back instead of finishing it yourself (see [Roles](#roles)).

## Step 0 — Start or resume

**Options** (strip them before reading the task):

| Option | Effect |
|---|---|
| `--spec <path>` | A requirements, ticket, or design file to treat as the starting requirements. |
| `--max-iterations N` | Iteration limit before stopping to ask. Default 5. An iteration may carry several lanes. |
| `--lanes N` | Most slices built in parallel per iteration. Default 3, or 1 when the checks can't run in two worktrees at once (see setup step 3). |
| `--verify auto\|full\|light` | `auto` (default) picks light verify for slices that qualify; `full` always uses a reviewer and a tester; `light` is only a preference, since a slice that doesn't qualify still gets full verify. |
| `--auto` | Don't pause at the requirements and design gates. Record assumptions and flag them in the report. Pushing and opening a PR still need the user. |
| `--dir <path>` | Work directory. Default `docs/sdlc/<slug>/`, where `<slug>` is a short kebab-case name for the work. |
| `--patterns <path>` | The file holding the user's implementation patterns. Default: the one found in Step 0, else `docs/patterns.md`. |
| `--models <role>=<model>,…` | Override a role's model, e.g. `--models architect=fable,verifier=opus`. Roles: `architect`, `engineer`, `reviewer`, `tester`, `verifier`, `final-reviewer`, `security-reviewer`, `skeptic`. Values: `sonnet`, `opus`, `fable`. See [Models](#models). |

**Resume.** If `<dir>/state.md` exists, read it and continue from the phase and iteration it records, lane by lane. Don't restart a phase whose artifact is already approved. Check that each open lane's worktree still exists (`git worktree list`); if one is gone, its uncommitted work is lost, so re-plan that slice.

**Otherwise set up:**

1. **Branch.** If on the default branch, create `sdlc/<slug>`. If the working tree already has uncommitted changes, ask whether they belong to this work; never sweep someone's unrelated changes into your commits.
2. **Checks.** Find the project's test, lint, format, typecheck, build and coverage commands (`CLAUDE.md`, package manifests, `Makefile`, CI config). Record them in `state.md`. Also record how to run **part** of the suite: by path or package (`pytest tests/orders`, `go test ./orders/...`, `cargo test -p orders`), and by related files where the runner supports it (`jest --findRelatedTests <files>`, `vitest related <files>`). This is the **targeted test command** that verify uses. Note how long the full suite takes, if CI or a recent run says. If the project has no checks, setting them up becomes the first backlog item, because the loop can't verify anything without them.
3. **Lanes.** Decide whether checks can run in two git worktrees at the same time. They can't if the tests use a fixed port, a shared local database or queue, or a build or cache directory outside the tree that two runs would overwrite. Record `parallel-safe: yes | no (<reason>)`. Record the **worktree setup command**, which is whatever a fresh checkout needs before checks run (`npm ci`, `uv sync`, copying a `.env` from the main checkout), or `none`. Record the worktree root `<repo parent>/<repo name>.worktrees/`. It sits outside the repo so test runners and linters in the main checkout don't pick the lanes up. If not parallel-safe, lanes default to 1 unless the user says otherwise.
4. **Scanners.** Look for security tooling the project already uses or has installed: a dependency audit (`npm audit`, `pip-audit`, `cargo audit`, `govulncheck`), a secret scanner (`gitleaks`, `trufflehog`), and static analysis (`semgrep`, `bandit`, CodeQL, security lint rules). Record the commands in `state.md` and run each once now to record a baseline of existing findings, so later runs can tell what this work introduced. Don't install new tools without asking. Where a category has no tool, record `none` and say so in the report, so nobody assumes it was checked.
5. **Languages.** Identify the languages this work will touch, from the manifests and the files in scope. Record each in `state.md` with its reference file in `references/languages/`, if there is one, and the formatter and linter the project uses for it. If a language has neither configured, add an optional backlog item proposing them; don't add tools or rules without the user's approval.
6. **Patterns.** Find where the user's implementation patterns are written: `--patterns`, else `docs/patterns.md`, else a patterns or conventions section in `CLAUDE.md`, `CONTRIBUTING.md` or an architecture doc. Record the path. Finding nothing is normal: record `docs/patterns.md` as where they will go, and create it when the first pattern is captured (see [Standards](#standards)).
7. **Roles.** Resolve each role to an agent type and a model (see [Roles](#roles)), applying `--models`, and record the mapping.
8. **Create the work directory.** Read [references/templates.md](references/templates.md) in full, then create each file from its template. Start the Timing log in `state.md` with the current time.
9. **Tell the user** in two or three lines what will happen: the phases, the lanes, where artifacts go, that each passing iteration is committed locally on the branch, and that nothing is pushed without their go-ahead.

```
<dir>/
├── state.md           # ledger: iteration, phase per lane, criteria status, checks, lanes setup, scanners, standards, roles, timing log
├── requirements.md    # goal, non-goals, numbered acceptance criteria and invariants
├── design.md          # approach, contracts, data model, decisions, risks, threat model
├── backlog.md         # ordered slices, follow-ups, quarantined flaky tests
├── iterations/02.md   # one per iteration: phases, lanes, integrate (merge + full suite), retro, timing
├── iterations/02a.md  # one per lane: plan, build, verify, lane completeness
├── iterations/02a/    # that lane's agent reports: engineer-r1.md, reviewer-r1.md, tester-r1.md, …
├── release/           # final-review.md, security.md, skeptic-<finding>.md
└── release.md         # PR description, written at Release
```

Update `state.md` every time a lane's phase changes. It is what makes the run resumable.

The patterns file is the exception to "everything in the work directory": it lives in the project (default `docs/patterns.md`), because it outlasts this piece of work and the next run should find it.

## Roles

| Role | Does | Model | Use a session agent like | Otherwise |
|---|---|---|---|---|
| **Driver** (you) | Requirements, planning, lanes, small design notes, retro, routing, gates | the session's | — | — |
| **Architect** | Design, threat model, and design changes that touch a contract, the data model, a trust boundary or a dependency | `opus` | `*-architect` | `general-purpose` |
| **Engineer** | Writes and fixes code and its unit tests, one per lane | `sonnet` | `software-engineer` | `general-purpose` |
| **Reviewer** | Read-only review of each slice: correctness, security, patterns, language practices; returns a verdict | `opus` | `code-reviewer` | `general-purpose` |
| **Tester** | Adds the missing tests for the slice's criteria and invariants and runs the targeted tests | `sonnet` | `qa-*`, `*-tester` | `general-purpose` |
| **Verifier** | Reviewer and tester in one, for a slice that qualifies for [light verify](#light-verify) | `sonnet` | — | `general-purpose` |
| **Final reviewer** | Whole-branch review at Release | `opus` | same as Reviewer | `general-purpose` |
| **Security reviewer** | Whole-branch security pass at Release | `opus` | `security-*` | `general-purpose` |
| **Skeptic** | Tries to disprove BLOCKER findings at Release | `opus` | — | `general-purpose` |

Prefer a custom agent from the session's agent list when one fits the role and the project's domain. Otherwise use `general-purpose` with the role brief from [references/roles.md](references/roles.md). Give every agent that brief's output contract either way, because the loop depends on the verdict lines. Say in the report which agent and model played each role.

**Launching.** With one lane, launch agents in the foreground when the next step needs their result. With several lanes, launch each lane's agents in the background (`run_in_background: true`) and handle each lane as its agent finishes: verify lane a as soon as its engineer is done, while lane b is still building. Don't wait for every lane at each phase. Launch agents that start at the same moment (a lane's reviewer and tester, or all the engineers at the start of an iteration) in one message.

Keep each lane's engineer ID for the whole iteration and continue the same agent for fix rounds (SendMessage), so it keeps its context. Keep the lane's reviewer and tester IDs too, because [delta rounds](#fix-rounds-are-delta-rounds) continue them. Start every role fresh in a new iteration.

**Reports.** Give every agent a report path: `<dir>/iterations/<NNx>/<role>-r<round>.md` inside a lane, `<dir>/release/<role>.md` at Release. The agent writes its whole output contract there and replies with its verdict line and the path. When a read-only agent returns the report in its reply, save the reply to the path yourself, unchanged.

**Contract check.** When an agent replies, open its report and check it against the Contract check table in [references/roles.md](references/roles.md). If anything is missing, send the same agent back for it (SendMessage) and name exactly what is missing. Don't fill the gap yourself, and don't read a verdict into a report that doesn't state one. A send-back is not a fix round. If a report is still incomplete after two returns, launch a fresh agent in the same role and model with the same hand-over, and note it in the `state.md` log. Count every send-back; the completeness check asks for the number.

### Models

The model follows what a mistake costs and how often the role runs:

- **`opus`** for judgment: the design, the full per-slice review, the whole-branch passes at Release, and the skeptics.
- **`sonnet`** for high-volume work that is well specified and independently checked: the engineer, the tester, and the light verifier. The verifier only runs on slices too small and contained for a sonnet review to miss much, and the final review at Release reads them all again.
- **`fable`** is never a default. It is the strongest and most expensive model, so the user opts in with `--models`. It pays off most where a role runs once or rarely and everything after depends on it: the architect, and the final and security reviewers.

Pass `model` on every launch, to custom agents as well. The driver is the model the session runs on; run the session on `opus` or `fable`, because requirements, lanes, routing and the loop decision are judgment work.

**Escalate when stuck, not by default.** If the same item is still open after two fix rounds, run the third round with a fresh `opus` engineer, handed the lane file, the diff and the open items. If the slice then routes back to Plan anyway, the next iteration's engineer starts on `sonnet` again.

**If a model isn't available,** use the next one down (`fable` → `opus` → `sonnet`) and name the substitution in the report. Don't move a role up a tier without `--models`, apart from the escalation above: the user is the one paying for it.

## Standards

Two things shape how the code is written, beyond whether it works: the user's own implementation patterns, and the practices of each language. Every agent that writes or judges code is handed both. Where they disagree, the higher one wins:

1. **The user's patterns** (`PAT-n` in the patterns file).
2. **Project rules:** `CLAUDE.md`, `CONTRIBUTING.md`, and the linter and formatter config.
3. **The existing code** around the change.
4. **The language reference** in [references/languages/](references/languages/).

Standards apply to code this work adds or changes. Existing code that breaks one is an optional backlog follow-up at most, never a reason to widen a slice.

### Patterns

A pattern is a rule about how the user wants things built: "handlers never touch the database", "money is an integer of minor units", "one module per feature". Each has an ID, a strength (`must` or `should`), where it applies, an exemplar file that shows it done right, and a check where a tool can enforce it. The format is in [references/templates.md](references/templates.md).

**Capture them as the work goes** instead of asking for a document up front:

- **At Requirements.** Read the code this work will touch, infer the two to four candidate patterns that matter most for it, and offer them in the same round of questions (one multi-select question) for the user to confirm, correct or reject. Also ask whether there is anything they always want done a certain way in this area.
- **At any correction.** When the user says "not like that, do it this way", ask whether it is a rule for next time or only for this case. A rule becomes a pattern.
- **At Retro.** If two slices (or two lanes) solved the same problem differently, propose a pattern that settles it.

Write down only what the user confirmed, and make it concrete enough to check. Never edit or drop an existing pattern without asking. Under `--auto`, record inferred patterns as `(proposed)`, treat them as `should`, and list them in the report.

**Exemplars.** Point each pattern at existing code that shows it. If none exists, the first slice that implements the pattern produces one, and after it integrates you show the user the file and ask whether it is the pattern as they meant it. **Lanes and exemplars:** don't put two slices that would each create the first exemplar of the same pattern in parallel lanes, or you get two versions of it. Build the first one; the other goes in a later iteration or follows it in the same lane.

**Enforcement.** A pattern a tool can check should be checked by a tool: propose the lint rule or script as a backlog item, and once it exists it runs with the other checks. The rest are checked in review. Breaking a `must` pattern is at least a MAJOR finding. Breaking a `should` is MINOR, unless the code says why it deviates.

If a pattern can't be followed in a slice, or two patterns conflict, nobody improvises. The agent reports it and it goes to the user (see [Routing](#routing-failures-back)).

### Language practices

For each language recorded in `state.md`, hand agents the matching file in `references/languages/` ([python.md](references/languages/python.md), [typescript.md](references/languages/typescript.md)), by absolute path.

- **Tools decide style.** Formatting, and anything the linter covers, is settled by running the formatter and linter as checks, not by review comments.
- **A practice matters when breaking it causes something.** A language-practice finding is BLOCKER or MAJOR only with a concrete failure. Idiom alone is MINOR.
- **No reference file for a language?** The agent names the standard it is applying at the top of its output. To add a language, copy [references/languages/_template.md](references/languages/_template.md).

## Phase 1 — Requirements (driver)

Write `requirements.md`: the goal, non-goals, numbered acceptance criteria (`AC-1`, `AC-2`, …), and numbered invariants (`INV-1`, …): existing behavior and rules that must not break.

- Start from `--spec`, the user's words, and any ticket or doc they reference. Read the relevant code first, so your questions are about real gaps and not things the repo already answers.
- Each criterion must be **testable**: a concrete input or state and an observable outcome.
- Write each invariant as concretely as a criterion: "a user never sees another tenant's orders", not "keep it secure".
- Where the request is ambiguous, ask with AskUserQuestion: at most 4 questions, each offering your best reading as the first option. In the same round, confirm the patterns (see [Patterns](#patterns)). One round of questions, not several.

**Gate:** show the criteria and get the user's approval. Under `--auto`, mark unconfirmed criteria `(assumed)` and continue.

**Later iterations:** apply only what the retro queued. A changed or added criterion goes back through the gate; a clarification doesn't.

## Phase 2 — Design

**First iteration (architect).** Launch the architect with `requirements.md` and the repo path. It writes `design.md` and ends with `DESIGN: READY` or `DESIGN: NEEDS_INPUT` plus its questions, which you put to the user. Scale it to the work: a small change in an existing codebase needs a few lines. If no design is needed and the change crosses no trust boundary, write that in `design.md` with the reason and skip the agent.

The design includes the patterns per component and a **threat model**: trust boundaries, what an attacker would want, and the abuse cases worth defending against. The architect proposes a security criterion for each abuse case; add them to `requirements.md` tagged `[security]`. If the work adds no attack surface, the design says so with the reason. That statement, made now by the architect, is the only thing that lets the security pass at Release be skipped.

The architect also marks the **dependencies between components**: which ones need another's contract to exist first. That is what Plan uses to find slices that can run in parallel.

**Gate:** summarize the approach, the main trade-off, anything hard to reverse (schema, public API, new dependency), any pattern exception, and the security criteria the threat model added, and get approval. Under `--auto`, record the decisions as assumed.

**Design changes later on.** Sort the change first, because most changes don't need the architect or the user:

| The change | Who | Gate |
|---|---|---|
| Touches a contract other code depends on, the data model, a trust boundary, or adds a dependency | Architect, sent only the delta (the finding and the sections it affects); the threat model is updated with it | Yes |
| Anything else: an internal structure, a helper's shape, the order of steps, a file that moves | The driver, as a dated line under Decisions in `design.md` saying what changed and why | No |

While a gated change waits for the user, don't stop every lane. A lane the change doesn't touch keeps building and verifying in the background: launch its next agents first, then ask. Collect the questions that come up in an iteration and ask them together, unless one blocks every lane.

## Phase 3 — Plan the iteration (driver)

On the first iteration, split the work into slices in `backlog.md`. A slice is **vertical** (it produces behavior you can test), small enough to build and review in one sitting, and mapped to the criteria it satisfies. For each slice, write the files it will likely touch and what it depends on. Put the riskiest or most uncertain slice early: if the design is wrong, you want to find out in iteration 1.

Each iteration, choose the **lanes**: up to `--lanes` slices from the top of the backlog that are independent. Two slices are independent when:

- neither needs code or a contract the other one creates;
- their likely files don't overlap, apart from append-only registration points (a route table, an export index, a test list), which the driver merges by hand;
- they don't both change the data model, a migration sequence, or a lockfile;
- they wouldn't both create the first exemplar of the same pattern.

Taking the second slice from further down the backlog is fine if the top two aren't independent; the backlog order is a priority, not a sequence. The riskiest slice goes in lane a. When in doubt, use fewer lanes. A conflict at merge costs more than the lane saved.

Write the iteration file with its Lanes table, and one lane file per lane with the plan section: the slice, its criteria, the invariants it could affect, the patterns that apply and their exemplars, files likely touched, what "done" means, and whether it qualifies for [light verify](#light-verify).

**Set up each lane:**

- **One lane:** work in the main checkout on the `sdlc/<slug>` branch.
- **Several lanes:** for each one, `git worktree add -b sdlc/<slug>-<NNx> <worktree root>/<slug>-<NNx> sdlc/<slug>`, then run the worktree setup command in it. Every agent in that lane is told to work only in that path.

Record each lane's **base commit** (the `sdlc/<slug>` head it started from) in its lane file.

## Phase 4 — Build (engineer, per lane)

Launch each lane's engineer with paths to `requirements.md`, `design.md`, the lane file, the patterns file and the language references, the lane's working path, the check commands, and the targeted test command. Ask it to read the exemplars before writing, implement only this slice, write unit tests for its own code, run the formatter, linter, typecheck and the targeted tests for the code it changed, and finish with a summary, the changed files, one line per pattern the plan lists, and the check output. It doesn't run the full suite; Integrate does.

When its report passes the contract check, fill in the Build section of the lane file. Leave out the engineer's account of how the code works, because the reviewer and tester read that file. Then make a **round commit** in the lane's checkout, staging only the files the engineer reported: `<slug> it NNx r1 (wip)`. Round commits give each later round a precise diff, and they are squashed into one commit at Integrate.

If the engineer reports that the slice can't be built as designed, don't push it to improvise. That is a routing event (see below).

## Phase 5 — Verify

Each lane is verified on its own, as soon as its build is done. The diff under review is `git diff <lane base>..HEAD` in the lane's checkout, plus any untracked files.

**Full verify** (the default): launch the reviewer and the tester in **one message**, each with fresh context.

- **Reviewer:** the requirements, design and lane plan paths, the patterns file and language references, the changed-file list, and the diff command. It reviews correctness, the slice's security against the threat model, every pattern the plan lists, and the language reference's bug sources and security pitfalls. It walks every branch, input boundary and external call in the changed code. Returns `VERDICT: APPROVED | CHANGES_REQUESTED` with findings marked BLOCKER, MAJOR or MINOR, and an `UNTESTED CASES` list.
- **Tester:** the requirements and lane plan paths, the language references, the targeted test command and the changed-file list. It reads the existing tests for the changed code first, including the engineer's, and adds tests **only for cases no existing test covers**: each criterion's main case, boundary and failure case, each listed invariant with no test yet, and the cases the implementation introduces. A `[security]` criterion is tested by making the attacker's request and asserting it is refused. It runs the **targeted** tests (the changed code's tests and its own new ones), not the full suite. Returns `RESULT: PASS | FAIL` with one row per criterion and invariant.

Expected results come from the requirements and design, never from what the code happens to do. When neither says what should happen, the case is `UNSPECIFIED`: the tester reports it with the code's current behavior instead of asserting it is right.

Don't give either of them the engineer's summary or its report path.

### Light verify

A lane qualifies when **all** of these hold, decided at Plan and written in the lane file:

- under about 200 changed lines, not counting tests;
- no `[security]` criterion in the slice, and the slice changes no trust boundary, entry point, permission, query built from input, secret, or stored personal data;
- no change to a contract other code depends on, the data model, or a dependency;
- every pattern it applies already has a confirmed exemplar.

Then one **verifier** (sonnet) does both jobs: it reviews the diff and adds and runs the missing tests, with the combined output contract in [references/roles.md](references/roles.md). If the actual diff turns out larger, or touches something on the list above, the lane goes to full verify instead. If the verifier reports a BLOCKER, or any finding that starts `security:`, the lane's next round is a full verify.

With `--verify full`, no lane uses light verify.

### After a round

**If everything passes** and nothing is listed as untested or unspecified, the lane goes to Integrate.

- **Untested cases** from the reviewer: continue the same tester to cover them. A test that then fails joins the fix list.
- **Unspecified cases:** settle each one yourself only when the requirements or design clearly imply the answer. Otherwise collect them and ask the user in one batch per iteration (under `--auto`, record the current behavior as assumed). Each answer becomes a criterion or invariant with a test.
- **MINOR findings** never go to the engineer and never hold the lane. Copy each to `backlog.md` as an optional follow-up, with its report and ID.
- **Flaky tests** follow the [flaky tests](#flaky-tests) rule, not the fix list.

**Otherwise** merge the BLOCKER and MAJOR findings and the failing tests into one numbered list, copied from the reports, and send it verbatim to the same engineer. Ask for a reply per item: `[#n] fixed: <how>` or `[#n] disputed: <reason>`. Make a round commit for the fix, then run a delta round.

### Fix rounds are delta rounds

A fix round changes a small part of a slice that has already been read and tested, so the second look is only at that part:

- **Reviewer:** continue the same reviewer. It gets the open findings, the engineer's replies, and the **fix diff** (`git diff <previous round commit>..HEAD`). It confirms each finding resolved or not, and reports new findings only in the fix diff or in code the fix diff's changes affect (callers of a changed function, a changed contract's users). It doesn't re-review the untouched rest of the slice.
- **Tester:** continue the same tester. It re-runs the tests that failed, the tests related to the files in the fix diff, and writes tests for the reviewer's untested cases. Not the whole targeted set again, and not the full suite.
- **Verifier** (light verify): both of the above, as one agent.

Allow **3 fix rounds** per lane. If an item is still open after two, the third goes to a stronger engineer (see [Models](#models)). Pass a disputed item back to whoever raised it, with the engineer's reasoning; it is withdrawn or restated with evidence. An item disputed twice is no longer a code problem, so route it.

### Flaky tests

A test that fails and then passes on a rerun with no change is flaky. The tester reruns it **up to 20 times, or 5 minutes**, whichever comes first, and reports it as `FLAKY` with the pass rate. Nobody hunts it further inside the round.

- **The slice didn't add the test or touch the code it tests:** it isn't this lane's problem. Add a `flaky` item to `backlog.md` (test, pass rate, the output of a failing run) and carry on. Name it in the iteration's status line so the user knows.
- **The slice added the test or changed the code it tests:** it goes to the engineer as one fix-list item, "make deterministic", with the failing output. If it is still flaky after that round, add a `must` backlog item, mark the criterion it verifies as unverified (it isn't verified by a test that passes sometimes), and let the lane go to Integrate with that gap written in its completeness table.

At the full suite in Integrate, a failure in a test the backlog already lists as flaky is rerun once; it doesn't stop the merge if it then passes.

## Phase 6 — Integrate (driver)

Lanes are merged one at a time, in lane order, and the full suite runs once on the result.

**For each lane that finished Verify:**

1. **Lane checks** in its checkout: the formatter, linter, typecheck, build, and any pattern checks, plus the scanners recorded in `state.md` compared with the baseline. A finding this work introduced goes back to the engineer as a fix round. A finding that was already there goes in the backlog once as optional.
2. **Completeness check.** Fill in the completeness table in the lane file, counting from the reports in `iterations/<NNx>/` and the output of step 1, not from memory. Where "done" is short of "expected":
   - for a criterion or invariant in the slice (other than one marked unverified for a flaky test), a `must` pattern, a BLOCKER or MAJOR finding, a failing check, or a missing section or report, go back to the phase that owes it. The lane isn't merged yet.
   - for anything else, write the reason in the table and add a backlog or open item.

   Don't change a number to make a row agree.
3. **Squash and merge.** Squash the lane's round commits into one: `git reset --soft <lane base>` and commit, following the repo's commit conventions and naming the criteria covered, e.g. `<slug>: iteration 2b — CSV export (AC-3, AC-4)`. With one lane this happens on `sdlc/<slug>` itself and you're done. With several, cherry-pick the squashed commit onto `sdlc/<slug>` in the main checkout. A conflict in an append-only registration point you resolve by hand. Any other conflict means the lanes weren't independent: abort the cherry-pick, send the lane back to its engineer to rebase onto the new `sdlc/<slug>` head, and verify the rebased lane with a delta round.

**Once every lane in the iteration is merged** (or routed back):

4. **Full suite once.** Run every check on `sdlc/<slug>`: the whole suite plus the formatter, linter, typecheck and build. Record the commit it ran on. This is the run that catches one slice breaking another.
5. **If it fails,** find the lane that caused it from the failing tests and the files each lane changed. Send the failure to that lane's engineer (continue it, and tell it to work in the main checkout now). After the fix, rerun the failing tests and the targeted tests for the fix, then the full suite once more. A failure no lane explains goes to a fresh engineer with all lane files.
6. **Clean up.** Remove the merged lanes' worktrees and branches (`git worktree remove`, `git branch -D sdlc/<slug>-<NNx>`). Keep a lane that was routed back until the next iteration picks it up.
7. **Update the criteria table** in `state.md`: a criterion or invariant is **verified** only with a passing test or check named beside it, from the full-suite run.
8. **Exemplars.** If a slice produced the first exemplar of a pattern, show the user the file and ask whether it is the pattern as they meant it. Under `--auto`, leave it provisional and list it in the report.

Don't push here.

## Phase 7 — Retro and loop decision (driver)

Write the retro section of the iteration file. Keep it short and specific:

- **Delivered:** criteria verified this iteration, per lane.
- **Learned:** anything that changes the plan, such as a wrong assumption, a design weakness, a slice that was bigger than it looked, or two lanes that turned out not to be independent.
- **Time:** the slowest phase and lane this iteration, from the Timing table, and whether anything about it should change next time (smaller slices, fewer lanes, a test-command problem).
- **Queued:** new backlog items (bugs, deferred MINOR findings, flaky tests, follow-ups), pattern candidates, and anything for the next iteration's Requirements or Design.

Then re-order the backlog and decide:

| Decision | When |
|---|---|
| `CONTINUE` | Criteria are still unverified or `must` backlog items remain, and this iteration made progress. Start the next iteration at Phase 1 or 2 if the retro queued something for them, otherwise at Phase 3. |
| `RELEASE` | Every criterion is verified, every invariant is covered by a test or marked untouched with the reason, and no `must` item remains. Optional items, MINORs included, don't hold release. |
| `ASK` | A stop condition was hit (see [Limits](#limits)). |

Give the user a one-line status after each iteration, e.g. `Iteration 2 (3 lanes, 41 min): AC-3, AC-4, AC-6 verified (5/7). 1 flaky test quarantined. Next: permissions slice.` Don't wait for a reply unless the decision is `ASK`.

## Release

1. **Final review and security pass**, launched in one message, each a fresh agent on the whole branch diff against the base:
   - **Final review.** Slice-by-slice review misses what only shows across slices, and with lanes even more so: duplicated helpers written in parallel, inconsistent naming, leftover scaffolding, a contract one slice changed under another, a pattern applied one way in one lane and another way in the next. It also reads the slices that had light verify as closely as the rest.
   - **Security pass.** It confirms that every abuse case in the threat model has a mitigation in the code and a test, then looks for what per-slice review can't see. Skip it only if `design.md` states the work adds no attack surface.
2. **Skeptic check.** For each BLOCKER from either agent, launch a fresh-context skeptic (all in one message) with only the claim, the location, the failure scenario and the diff command, and ask it to disprove the finding. It replies `CONFIRMED`, `PLAUSIBLE` or `REFUTED` with evidence. Drop refuted findings and list them in the report as checked.
3. **Full checks and scanners.** If `sdlc/<slug>` is still at the commit the last Integrate ran the full suite on, and that run passed, reuse its result and name the commit. Otherwise run them once.
4. **Findings re-enter the loop.** Confirmed and plausible BLOCKERs, and MAJOR findings, become backlog items and you run another iteration. **MINOR findings don't**: they go in `release.md` under follow-ups, and get an iteration only if the user asks for one.
5. **Completeness check.** When no BLOCKER or MAJOR remains, fill in the Completeness table of the [report](#report), counting from the files. A shortfall is a backlog item and another iteration, not a note in `release.md`.
6. When clean, write `release.md`: what changed, the criteria table with the test that verifies each one, the security summary, design decisions worth a reviewer's attention, known limits, and follow-ups (MINORs, quarantined flaky tests).
7. **Gate:** show the summary and ask before pushing or opening a PR. These publish on the user's behalf, so `--auto` doesn't cover them.
8. **After the PR**, CI failures and review comments are feedback like any other: add them to the backlog and run another iteration. The loop ends when the user says the work is done.

## Timing

Time is what this skill is for, so measure it. Without the numbers, the next change to the process is a guess.

- At the start and end of every phase, per lane, record the time (`date -u +%FT%TZ`) in the lane file or the iteration file.
- For each agent, record the duration its result or completion notification reports, when it reports one, beside its report path.
- Record when you asked the user at a gate and when they answered. That wait is real time, but it isn't the process's.
- Fill in the Timing table in the iteration file at Retro: wall-clock per phase, agent time per role, fix rounds per lane, full-suite runs and their duration, and user wait.

The report's Time section totals these across the run.

## Routing failures back

| Signal | Goes back to |
|---|---|
| Review finding (BLOCKER or MAJOR) or test failure where the code is wrong | Build, same lane |
| MINOR finding | Backlog, optional; never a fix round |
| Test is wrong (engineer disputes it and the tester agrees) | Tester, same lane |
| Flaky test | See [Flaky tests](#flaky-tests) |
| Criterion is ambiguous, untestable, or disputed twice | Requirements; ask the user |
| Engineer or reviewer shows the design can't satisfy a criterion | Design (sorted by the table in Phase 2), then re-plan the slice |
| Slice still failing after 3 fix rounds | Plan; split it or reorder, and note why in the retro |
| Scanner finding this work introduced | Build, same lane |
| A `must` pattern broken in the slice | Build, same lane |
| A pattern can't be followed here, or two patterns conflict | The user. Update the patterns file with the answer, then Design if it changes a contract |
| Security finding that needs a boundary or check the design doesn't have | Design, to update the threat model; add or fix the `[security]` criterion, then re-plan |
| Edge case the requirements and design don't cover (`UNSPECIFIED`) | Requirements; once settled it becomes a criterion or invariant |
| Merge conflict between lanes outside a registration point | The later lane's engineer, to rebase; then a delta round. Note in the retro that the lanes weren't independent |
| Full suite fails after merging | The lane whose changes caused it (Phase 6 step 5) |
| Regression in an earlier iteration's slice | Build, with that iteration's lane file as context |
| CI failure or PR comment after release | Backlog, next iteration |

When a failure routes backwards across phases, leave that lane unmerged, record the reason in the retro, and let the next iteration pick it up from the phase the failure points at. The other lanes merge as normal.

## Limits

Stop and ask the user (`ASK`) when any of these holds. Report the open items and offer concrete options instead of looping further:

- `--max-iterations` is reached.
- An iteration verified no new criterion and closed no `must` backlog item.
- The `must` items in the backlog grew in two consecutive iterations. This usually means the scope is wrong, not the code. Optional items, MINORs and quarantined flakes don't count.
- A requirement contradicts another, or the user's answer changes the goal.
- A check command can't be run in this environment, so verification isn't possible.

## Report

End every run, whether it finished or stopped, with:

```markdown
## SDLC Fast: <work>

**Status:** ✅ Ready to release | ⏸ Stopped: <reason> | 🔁 In progress (resumable)
**Branch:** `<branch>` · **Iterations:** <n> · **Lanes:** <n slices in total, most in parallel: n> · **Artifacts:** `<dir>`

### Acceptance criteria and invariants
| ID | Criterion | Status | Verified by |
|---|---|---|---|
| AC-1 | … | ✅ verified | `tests/…::test_name` |
| AC-2 [security] | … | ❌ open | — |
| INV-1 | … | ✅ verified | `tests/…::test_name` |

### Security
- **Threat model:** <each abuse case and the criterion that covers it, or "no new attack surface: <reason>">
- **Scanners:** <each tool and its result against the baseline; name every category that had no tool>
- **Release security pass:** <result; blockers confirmed and refuted by the skeptic; or why it was skipped>

### Patterns and standards
- **Patterns:** <each PAT-n that applied: followed, exception granted (reason), or open finding; patterns captured or proposed; exemplars awaiting confirmation>
- **Languages:** <each language, its reference file or the standard named instead, and the formatter and linter that ran>

### Iterations
- 1: a <slice> → <outcome, verify mode, fix rounds> · b <slice> → …
- 2: …

### Time
| | Wall-clock | Agent time | Notes |
|---|---|---|---|
| Requirements + design | | | user wait <n> min |
| Build | | | by lane |
| Verify | | | fix rounds: <n> across <n> lanes; light verify on <n> lanes |
| Integrate | | | full-suite runs: <n> × <duration> |
| Release | | | |
| **Total** | | | slowest phase: <phase, and why> |

### Completeness
| What | Expected | Done | Gap and reason |
|---|---|---|---|
| Criteria verified by a named test that passes on the final commit | 7 | 7 | |
| Invariants verified, or untouched with the reason | 3 | 3 | |
| Abuse cases with a criterion and a test | 4 | 4 | |
| Patterns that applied, with a reviewer or verifier result in every slice | 3 | 3 | |
| Lanes with every phase section and a completeness table | 5 | 5 | |
| Agent reports on disk, against agents launched | 23 | 23 | |
| Reports sent back for a missing contract section | — | 2 | |
| Release: final review, security pass, a skeptic per BLOCKER | 2 + 1 | 2 + 1 | |
| Checks and scanners run on the final commit | 5 + 2 | 5 + 2 | static analysis: no tool |

<for a run that stopped early, fill in the rows it reached and write "not reached" in the rest>

### Open items
<unverified criteria, unresolved or disputed findings, assumptions made under --auto>
<deferred MINOR findings and quarantined flaky tests, by backlog number>
<branches or edge cases in changed code that no test exercises, and why>

### Who did what
<role → agent type and model; any escalation, substitution or --models override; which lanes had light verify>
```

Agent output isn't visible to the user, so this report and the per-iteration status lines are all they see. State what wasn't done as plainly as what was.
