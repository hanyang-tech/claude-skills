---
name: sdlc-loop
description: Run the whole software development lifecycle as an iterative loop with multiple agents. Each iteration goes requirements → design → plan → build → review + test → integrate → retro, and the retro feeds the next iteration, until every acceptance criterion is verified and the branch is ready to release. Code follows the user's own implementation patterns and each language's practices, and review checks both. Use when the user wants a feature, project, or sizeable change taken end to end from an idea to a reviewed, tested, PR-ready branch; asks for an "SDLC", "full lifecycle", "end-to-end", "idea to PR", or iterative/agile multi-agent build; wants agents to plan, build, test and review in cycles; or invokes /sdlc-loop with a description of the work (options --spec, --max-iterations, --auto, --dir, --patterns, --models). Prefer this over a single build-and-review pass whenever requirements or design have to be settled first, or the work spans more than one slice.
---

# SDLC Loop

Take a piece of work from idea to release-ready by going round the lifecycle in iterations. Each iteration delivers one thin, working slice, and what it teaches you changes the next one.

Work to deliver: `$ARGUMENTS` (if empty, use the task from the conversation; if there is none, ask for it).

You are the **driver**. Subagents can't spawn each other and can't talk to the user, so you run the loop, hold the gates, and move files between roles. This skill is self-contained: it doesn't need any other skill to be installed.

## Principles

- **Loop, not waterfall.** Requirements and design are revisited every iteration, so they only need to be good enough to build the next slice. Don't try to get them perfect up front; the first working slice will tell you more than another hour of planning.
- **Acceptance criteria are the exit condition.** The loop ends when every numbered criterion is verified, and every invariant covered, by a passing test or an explicit check. Without that list the loop has no principled way to stop, so nothing gets built until it exists.
- **State lives on disk.** Every phase writes to the work directory, and agents are handed file paths, not your summaries. This keeps each agent's context small, and it lets a run resume after a context summary or in a new session.
- **Independent roles.** The agent that wrote the code doesn't review or test it. The reviewer and tester get fresh context and never see the engineer's reasoning, so they judge the code against the criteria instead of against the author's story about it.
- **Security is checked where it's cheap.** Threats are named at design time and turned into criteria, each slice is reviewed for security as it is built, and scanners run at every integrate. A flaw that is only found at release already has other slices built on top of it.
- **A failure goes back to its cause.** A failing test isn't always a code problem; it can be an ambiguous criterion or a design that can't work. Send each failure to the phase that owns the cause (see [Routing](#routing-failures-back)).
- **Relay faithfully.** Pass findings between agents verbatim. Don't soften, drop, or add to them, and never record a verdict an agent didn't give.

## The loop

```
        ┌──────────────── next iteration: criteria or backlog remain ───────────────┐
        ▼                                                                           │
  1 Requirements → 2 Design → 3 Plan → 4 Build → 5 Verify → 6 Integrate → 7 Retro ──┤
        ▲              ▲         ▲         ▲         │     (review + test)          │
        └──────────────┴─────────┴─────────┴─────────┘                              ▼
              a failure routes back to the phase that caused it        all criteria pass → Release
                                                                                    │
        ┌───────────── CI failures and PR comments re-enter as backlog ─────────────┘
```

Phases 1 and 2 are **revisited, not redone**. From iteration 2 on, run them only if the previous retro queued something for them; otherwise note "no change" in the iteration file and go straight to Plan.

## Working method

A long run drifts. Phases get merged, a brief gets paraphrased from memory, an agent's half-answer gets finished by the driver. Each of these leaves the run looking complete while a step was skipped. Five habits make a skipped step visible instead:

**1. Read the reference before the step that uses it.** The references are instructions, not background, and this file doesn't repeat them.

| Before | Read, in this run |
|---|---|
| Creating the work directory, and the first time you write each artifact | [references/templates.md](references/templates.md), the whole file |
| Launching a role, each iteration | That role's section of [references/roles.md](references/roles.md), and its row in the Contract check table there. The brief and the output contract go to the agent as written, with the placeholders filled in, not as you remember them |
| Planning a slice, and checking a report's `PATTERNS` lines | The patterns file |
| Resuming, or carrying on after a context summary | `state.md`, the current iteration file, then the rows above for the phase you are in. A summary doesn't carry the briefs or the templates |

The language references are for the agents. Your part is to check that each file exists and to hand over its absolute path.

**2. One task per phase.** At the start of each iteration, fill in the `Phases` checklist at the top of the iteration file. If the session has a task list (TaskCreate or TodoWrite), also create a task for each of the seven phases, named like `It. 2 · 5 Verify`. Do the same for the steps of Release. The tasks show the user where the run is; the checklist is what survives a context summary. A phase with nothing to do, such as Requirements with nothing queued, is ticked with "no change", not left out.

**3. A phase is done when its output is on disk,** not when its agent returns. Tick it, and close its task, only then:

| Phase | On disk before the next phase starts |
|---|---|
| 1 Requirements | `requirements.md` updated and its gate recorded in `state.md`; or "no change" in the iteration file |
| 2 Design | `design.md` and the architect's report (no report when the design was skipped with its reason); or "no change" |
| 3 Plan | The Plan section of the iteration file |
| 4 Build | The engineer's report, and the Build section |
| 5 Verify | A reviewer report and a tester report for every round, and a row per round in the Verify section |
| 6 Integrate | The Integrate section with its completeness table, the commit, and the criteria table in `state.md` |
| 7 Retro | The Retro section with its `DECISION` |

**4. Count before committing and before releasing.** [Phase 6](#phase-6--integrate-driver) and [Release](#release) each have a completeness check: what was expected against what was done, counted from the files. Numbers that don't match send you back to the phase that owes the work.

**5. Check every agent report against its contract,** and send an incomplete one back instead of finishing it yourself (see [Roles](#roles)).

## Step 0 — Start or resume

**Options** (strip them before reading the task):

| Option | Effect |
|---|---|
| `--spec <path>` | A requirements, ticket, or design file to treat as the starting requirements. |
| `--max-iterations N` | Iteration limit before stopping to ask. Default 5. |
| `--auto` | Don't pause at the requirements and design gates. Record assumptions and flag them in the report. Pushing and opening a PR still need the user. |
| `--dir <path>` | Work directory. Default `docs/sdlc/<slug>/`, where `<slug>` is a short kebab-case name for the work. |
| `--patterns <path>` | The file holding the user's implementation patterns. Default: the one found in Step 0, else `docs/patterns.md`. |
| `--models <role>=<model>,…` | Override a role's model, e.g. `--models architect=fable,security-reviewer=fable`. Roles: `architect`, `engineer`, `reviewer`, `tester`, `final-reviewer`, `security-reviewer`, `skeptic`. Values: `sonnet`, `opus`, `fable`. See [Models](#models). |

**Resume.** If `<dir>/state.md` exists, read it and continue from the phase and iteration it records. Don't restart a phase whose artifact is already approved.

**Otherwise set up:**

1. **Branch.** If on the default branch, create `sdlc/<slug>`. If the working tree already has uncommitted changes, ask whether they belong to this work; never sweep someone's unrelated changes into your commits.
2. **Checks.** Find the project's test, lint, format, typecheck, build and coverage commands (`CLAUDE.md`, package manifests, `Makefile`, CI config). Record them in `state.md`. If the project has none, setting them up becomes the first backlog item, because the loop can't verify anything without them.
3. **Scanners.** Look for security tooling the project already uses or has installed: a dependency audit (`npm audit`, `pip-audit`, `cargo audit`, `govulncheck`), a secret scanner (`gitleaks`, `trufflehog`), and static analysis (`semgrep`, `bandit`, CodeQL, security lint rules). Record the commands in `state.md` and run each once now to record a baseline of existing findings, so later runs can tell what this work introduced. Don't install new tools without asking. Where a category has no tool, record `none` and say so in the report, so nobody assumes it was checked.
4. **Languages.** Identify the languages this work will touch, from the manifests (`pyproject.toml`, `package.json`, `tsconfig.json`, `go.mod`, `Cargo.toml`) and the files in scope. Record each in `state.md` with its reference file in `references/languages/`, if there is one, and the formatter and linter the project uses for it. If a language has neither configured, add an optional backlog item proposing them; don't add tools or rules without the user's approval.
5. **Patterns.** Find where the user's implementation patterns are written: `--patterns`, else `docs/patterns.md`, else a patterns or conventions section in `CLAUDE.md`, `CONTRIBUTING.md` or an architecture doc. Record the path. Finding nothing is normal: record `docs/patterns.md` as where they will go, and create it when the first pattern is captured (see [Standards](#standards)).
6. **Roles.** Resolve each role to an agent type and a model (see [Roles](#roles)), applying `--models`, and record the mapping.
7. **Create the work directory.** Read [references/templates.md](references/templates.md) in full, then create each file from its template.
8. **Tell the user** in two or three lines what will happen: the phases, where artifacts go, that each passing iteration is committed locally on the branch, and that nothing is pushed without their go-ahead.

```
<dir>/
├── state.md          # ledger: iteration, phase, criteria status, checks, scanners, standards, role → agent and model
├── requirements.md   # goal, non-goals, numbered acceptance criteria and invariants
├── design.md         # approach, contracts, data model, decisions, risks, threat model
├── backlog.md        # ordered slices and follow-ups
├── iterations/01.md  # one file per iteration: phases, plan, build, verify, integrate, retro
├── iterations/01/    # each agent's report as it came back: engineer-r1.md, reviewer-r1.md, tester-r1.md, …
├── release/          # final-review.md, security.md, skeptic-<finding>.md
└── release.md        # PR description, written at Release
```

Update `state.md` every time the phase changes. It is what makes the run resumable.

The patterns file is the exception to "everything in the work directory": it lives in the project (default `docs/patterns.md`), because it outlasts this piece of work and the next run should find it.

## Roles

| Role | Does | Model | Use a session agent like | Otherwise |
|---|---|---|---|---|
| **Driver** (you) | Requirements, planning, retro, routing, gates | the session's | — | — |
| **Architect** | Design, threat model, and design changes | `opus` | `*-architect` | `general-purpose` |
| **Engineer** | Writes and fixes code and its unit tests | `sonnet` | `software-engineer` | `general-purpose` |
| **Reviewer** | Read-only review of each slice: correctness, security, patterns, language practices; returns a verdict | `opus` | `code-reviewer` | `general-purpose` |
| **Tester** | Writes and runs tests for the acceptance criteria and invariants | `sonnet` | `qa-*`, `*-tester` | `general-purpose` |
| **Final reviewer** | Whole-branch review at Release | `opus` | same as Reviewer | `general-purpose` |
| **Security reviewer** | Whole-branch security pass at Release | `opus` | `security-*` | `general-purpose` |
| **Skeptic** | Tries to disprove BLOCKER findings at Release | `opus` | — | `general-purpose` |

Prefer a custom agent from the session's agent list when one fits the role and the project's domain; it carries its own tools and working method. Otherwise use `general-purpose` with the role brief from [references/roles.md](references/roles.md). Give every agent that brief's output contract either way, because the loop depends on the verdict lines. Say in the report which agent and model played each role.

Launch agents in the foreground (`run_in_background: false`) when the next step needs their result. Keep the engineer's agent ID for the whole iteration and continue the same agent for fix rounds (SendMessage), so it keeps its context. Start the reviewer and tester fresh each iteration.

**Reports.** Give every agent a report path: `<dir>/iterations/<NN>/<role>-r<round>.md` inside an iteration, `<dir>/release/<role>.md` at Release. The agent writes its whole output contract there and replies with its verdict line and the path. Some read-only agents won't write a file; when one returns the report in its reply, save the reply to the path yourself, unchanged. These files are what the fix round, the next phase and the completeness checks read, so nothing is passed on from memory.

**Contract check.** When an agent replies, open its report and check it against the Contract check table in [references/roles.md](references/roles.md): every line and section of the contract is there, everything the plan lists has its own row (a `PATTERNS` line per pattern, a `CRITERIA` row per criterion and invariant), and a section with nothing to say reads `none`. If anything is missing, send the same agent back for it (SendMessage) and name exactly what is missing. Don't fill the gap yourself, and don't read a verdict into a report that doesn't state one. You would be doing the skipped work with less of the code in view than the agent has and none of its independence, and the run would then record your guess as its result. A send-back for a missing section is not a fix round and doesn't count towards the three. If a report is still incomplete after two returns, launch a fresh agent in the same role and model with the same hand-over, and note it in the `state.md` log. Count every send-back; the completeness check asks for the number.

### Models

The model follows what a mistake costs and how often the role runs:

- **`opus`** for judgment: the design, the per-slice review, the whole-branch passes at Release, and the skeptics.
- **`sonnet`** for high-volume work that is well specified and independently checked. The engineer's code is judged by the reviewer and the tester; the tester's tests are checked against the reviewer's untested-cases list and the coverage report.
- **`fable`** is never a default. It is the strongest model and the most expensive, so the user opts in with `--models`. It pays off most where a role runs once or rarely and everything after depends on it: the architect (every slice is built on the design) and the final and security reviewers (the last chance to catch what slice-by-slice review missed).

Pass `model` on every launch, to custom agents as well, so this table (or `--models`) decides and not whatever an agent definition happens to say. The driver is the model the session is running on, which the skill can't change. Requirements, routing and the loop decision are judgment work, so run the session on `opus` or `fable`.

**Escalate when stuck, not by default.** If the same item is still open after two fix rounds, run the third round with a fresh `opus` engineer, handed the iteration file, the diff and the open items. A continued agent keeps the model it started with, so escalating means a new agent. If the slice then routes back to Plan anyway, the next iteration's engineer starts on `sonnet` again.

**If a model isn't available** in this session, use the next one down (`fable` → `opus` → `sonnet`) and name the substitution in the report. Don't substitute silently. Apart from the engineer escalation above, don't move a role up a tier without `--models`: the user is the one paying for it.

## Standards

Two things shape how the code is written, beyond whether it works: the user's own implementation patterns, and the practices of each language. Every agent that writes or judges code is handed both. Where they disagree, the higher one wins:

1. **The user's patterns** (`PAT-n` in the patterns file).
2. **Project rules:** `CLAUDE.md`, `CONTRIBUTING.md`, and the linter and formatter config.
3. **The existing code** around the change.
4. **The language reference** in [references/languages/](references/languages/).

Standards apply to code this work adds or changes. Existing code that breaks one is an optional backlog follow-up at most, never a reason to widen a slice.

### Patterns

A pattern is a rule about how the user wants things built: "handlers never touch the database", "money is an integer of minor units", "one module per feature". Each has an ID, a strength (`must` or `should`), where it applies, an exemplar file that shows it done right, and a check where a tool can enforce it. The format is in [references/templates.md](references/templates.md).

**Most patterns start in the user's head, so capture them as the work goes** instead of asking for a document up front:

- **At Requirements.** Read the code this work will touch, infer the two to four candidate patterns that matter most for it, and offer them in the same round of questions (one multi-select question) for the user to confirm, correct or reject. People who can't list their patterns cold recognize a wrong one at once. Also ask whether there is anything they always want done a certain way in this area.
- **At any correction.** When the user says "not like that, do it this way" at a gate or after an iteration, ask whether it is a rule for next time or only for this case. A rule becomes a pattern.
- **At Retro.** If two slices solved the same problem differently, or an agent had to guess at the same structural choice twice, propose a pattern that settles it.

Write down only what the user confirmed, and make it concrete enough to check: "keep handlers thin" becomes "a handler parses the request, calls one service function, and maps the result to a response". Never edit or drop an existing pattern without asking. Under `--auto`, record inferred patterns as `(proposed)`, treat them as `should`, and list them in the report.

**Exemplars.** A written rule is followed far better when there is a file to copy. Point each pattern at existing code that shows it. If none exists, the first slice that implements the pattern produces one: after that slice integrates, show the user the file and ask whether it is the pattern as they meant it. Until they confirm, the exemplar is provisional; once confirmed, later slices copy it.

**Enforcement.** A pattern a tool can check (import boundaries, banned calls, naming, file layout) should be checked by a tool: propose the lint rule or script as a backlog item, and once it exists it runs with the other checks. The rest are checked in review, pattern by pattern. Breaking a `must` pattern is at least a MAJOR finding. Breaking a `should` is MINOR, unless the code says why it deviates.

If a pattern can't be followed in a slice, or two patterns conflict, nobody improvises. The agent reports it and it goes to the user (see [Routing](#routing-failures-back)).

### Language practices

For each language recorded in `state.md`, hand agents the matching file in `references/languages/` ([python.md](references/languages/python.md), [typescript.md](references/languages/typescript.md)). Each covers tooling, idioms, the bugs and security mistakes that language makes easy, testing conventions, and edge cases worth always trying. Give agents the file's absolute path, since they don't know where this skill is installed.

- **Tools decide style.** Formatting, and anything the linter covers, is settled by running the formatter and linter as checks, not by review comments. Reviewers don't report style that neither a pattern nor a tool enforces.
- **A practice matters when breaking it causes something.** A language-practice finding is BLOCKER or MAJOR only with a concrete failure, such as a mutable default shared between calls or an unawaited promise that drops an error. Idiom alone is MINOR.
- **No reference file for a language?** The agent names the standard it is applying (the language's official style guide plus the project's linter config) at the top of its output, so the choice is visible. To add a language, copy [references/languages/_template.md](references/languages/_template.md).

## Phase 1 — Requirements (driver)

Write `requirements.md`: the goal, non-goals, numbered acceptance criteria (`AC-1`, `AC-2`, …), and numbered invariants (`INV-1`, …): existing behavior and rules that must not break.

- Start from `--spec`, the user's words, and any ticket or doc they reference. Read the relevant code first, so your questions are about real gaps and not things the repo already answers.
- Each criterion must be **testable**: a concrete input or state and an observable outcome. "Works well with large files" isn't a criterion; "a 1 GB upload completes without loading the file into memory" is.
- Invariants get tested too, so write each one as concretely as a criterion: "a user never sees another tenant's orders", not "keep it secure". Bugs outside the stated criteria are usually a broken invariant nobody wrote down.
- Where the request is ambiguous, ask with AskUserQuestion: at most 4 questions, each offering your best reading as the first option. Don't ask what the code can tell you.
- In the same round, confirm the patterns this work should follow (see [Patterns](#patterns)). Confirmed ones go into the patterns file, not into `requirements.md`.

**Gate:** show the criteria and get the user's approval. Under `--auto`, mark unconfirmed criteria `(assumed)` and continue.

**Later iterations:** apply only what the retro queued, such as a criterion that turned out ambiguous, a new requirement from the user, or one that proved infeasible. A changed or added criterion goes back through the gate; a clarification doesn't.

## Phase 2 — Design (architect)

Launch the architect with `requirements.md` and the repo path. It writes `design.md` and ends with `DESIGN: READY` or `DESIGN: NEEDS_INPUT` plus its questions, which you put to the user.

Scale it to the work. A small change in an existing codebase needs a few lines: which files change and why. If no design is needed and the change crosses no trust boundary (no new input, endpoint, permission, secret, or stored data), write that in `design.md` with the reason and skip the agent.

**Patterns.** The architect reads the patterns file and says, for each component, which patterns apply and which existing file is the exemplar. Where the design it thinks best would break a pattern, it returns `NEEDS_INPUT` instead of deviating. An exception the user grants is recorded in `design.md` with its reason, so the reviewer doesn't report it every iteration.

**Threat model.** The design includes one: the trust boundaries the work crosses, what an attacker would want, and the abuse cases worth defending against. The architect proposes a security criterion for each abuse case. Add them to `requirements.md` as ordinary criteria tagged `[security]`, e.g. `AC-6 [security]` a member of one team gets a 404 for another team's report. They are then built, tested and tracked like any other criterion, instead of depending on a reviewer noticing the gap later. If the work adds no attack surface, the design says so with the reason; that statement, made now by the architect, is the only thing that lets the security pass at Release be skipped.

**Gate:** summarize the approach, the main trade-off, anything hard to reverse (schema, public API, new dependency), any pattern exception, and the security criteria the threat model added, and get approval. Under `--auto`, record the decisions as assumed.

**Later iterations:** send the same architect only the delta: the finding or failed slice that showed the design is wrong, and the sections it affects. A change to a contract, the data model, or a trust boundary goes back through the gate, and the threat model is updated with it.

## Phase 3 — Plan the iteration (driver)

On the first iteration, split the work into slices in `backlog.md`. A slice is **vertical** (it produces behavior you can test, not "all the models, then all the handlers"), small enough to build and review in one sitting, and mapped to the criteria it satisfies. Put the riskiest or most uncertain slice early: if the design is wrong, you want to find out in iteration 1.

Each iteration, take the top of the backlog (one slice; more only if they're small and touch different files) and write the plan section of `iterations/NN.md`: the slice, its criteria, the invariants it could affect, the patterns that apply and their exemplars, files likely touched, and what "done" means for this iteration.

## Phase 4 — Build (engineer)

Launch the engineer with paths to `requirements.md`, `design.md`, `iterations/NN.md`, the patterns file and the language references, plus the check commands. Ask it to read the exemplars before writing, implement only this slice, write unit tests for its own code, run the checks including the formatter, and finish with a summary, the changed files, one line per pattern the plan lists, and the check output.

When its report passes the contract check, fill in the Build section of the iteration file from it: the changed files, the check results and the pattern lines. Leave out its account of how the code works, because the reviewer and tester read that file.

If it reports that the slice can't be built as designed, don't push it to improvise. That is a routing event (see below).

## Phase 5 — Verify (reviewer and tester, in parallel)

Launch both in **one message**, each with fresh context:

- **Reviewer:** the requirements, design and plan paths, the patterns file and language references, the engineer's changed-file list, and how to see the diff. It reviews the slice's security every iteration, against the threat model, so a flaw is caught before the next slice builds on it. It also checks the slice pattern by pattern, and against the language reference's bug sources and security pitfalls. Returns `VERDICT: APPROVED | CHANGES_REQUESTED` with findings marked BLOCKER, MAJOR or MINOR.
- **Tester:** the requirements and plan paths, the language references and the check commands. It follows the language's testing conventions and writes tests for this slice's criteria, and for each invariant the plan names that has no test yet, from the requirements themselves. A `[security]` criterion is tested by making the attacker's request and asserting it is refused. It runs the full suite and returns `RESULT: PASS | FAIL` with one row per criterion and invariant.

**Edge cases come from the code as well as the criteria.** Criteria describe what was asked for; the implementation adds cases nobody asked about, such as a cache that can go stale, a page boundary, a retry, or a null from a new lookup. So both agents also work from the code:

- The reviewer walks every branch, input boundary and external call in the changed code. A case the code gets wrong is a finding. A case it handles but no test exercises goes in its `UNTESTED CASES` list.
- The tester, after its criteria tests, reads the implementation to find the cases it introduces and tests those too. Where the project has a coverage tool, it reports the uncovered branches in changed code and tests them or says why not.

Expected results still come from the requirements and design, never from what the code happens to do. When neither says what should happen, the case is `UNSPECIFIED`: the tester reports it with the code's current behavior instead of asserting that behavior is right.

No agent can try every possible input. The aim is that no branch, boundary or failure point in the changed code goes unexamined, and that the report says which ones weren't tested.

Don't give either of them the engineer's summary of how it works, or the path of its report. Running them together costs one fix round instead of two, and their findings often explain each other.

**If both pass** and nothing is listed as untested or unspecified, go to Integrate.

- **Untested cases** from the reviewer: continue the same tester to cover them before integrating. A test that then fails joins the fix list.
- **Unspecified cases:** settle each one yourself only when the requirements or design clearly imply the answer. Otherwise ask the user in one batch at the end of the iteration (under `--auto`, record the current behavior as assumed). Each answer becomes a criterion or invariant with a test.

**Otherwise** merge the reviewer's BLOCKER and MAJOR findings and the tester's failures into one numbered list, copied from the two reports, and send it verbatim to the same engineer. Ask for a reply per item: `[#n] fixed: <how>` or `[#n] disputed: <reason>`. Then re-verify: continue the same reviewer with the previous findings, and have the tester re-run.

Allow **3 fix rounds** per iteration. If an item is still open after two, the third goes to a stronger engineer (see [Models](#models)). Pass a disputed item back to whoever raised it, with the engineer's reasoning; it is withdrawn or restated with evidence. An item disputed twice is no longer a code problem, so route it.

## Phase 6 — Integrate (driver)

1. Run every check yourself, the whole suite plus the formatter, linter and any pattern checks, and not only this slice's tests, since a slice that passes its own tests can still break an earlier one.
2. Run the scanners recorded in `state.md` and compare with the baseline. A finding this work introduced (a vulnerable dependency it added, a secret it committed, a new static-analysis hit in changed code) goes back to the engineer as a fix round before committing. A finding that was already there isn't this iteration's job: add it to the backlog once as optional and move on.
3. **Completeness check.** Fill in the completeness table in the Integrate section of the iteration file. Count from the reports in `iterations/<NN>/` and from the output of steps 1 and 2, not from memory. Where "done" is short of "expected":
   - for a criterion or invariant in the slice, a `must` pattern, a BLOCKER or MAJOR finding, a failing check, or a missing phase section or report, go back to the phase that owes it. The slice isn't committed yet.
   - for anything else (an untested case that can't be reached in this environment, an unspecified case waiting for the user, a scanner category with no tool), write the reason in the table and add a backlog or open item.

   Don't change a number to make the row agree, and don't commit first and explain afterwards.
4. Commit locally on the branch. Stage only files this work touched, follow the repo's commit conventions, and name the criteria covered, e.g. `<slug>: iteration 2 — CSV export (AC-3, AC-4)`.
5. Update the criteria table in `state.md`: a criterion or invariant is **verified** only with a passing test or check named beside it.
6. If this slice produced the first exemplar of a pattern, show the user the file and ask whether it is the pattern as they meant it. A "no" is a fix for the next iteration and usually a sharper wording of the pattern. Under `--auto`, leave the exemplar provisional and list it in the report.

Don't push here.

## Phase 7 — Retro and loop decision (driver)

Write the retro section of `iterations/NN.md`. Keep it short and specific:

- **Delivered:** criteria verified this iteration.
- **Learned:** anything that changes the plan, such as a wrong assumption, a design weakness, or a slice that was bigger than it looked.
- **Queued:** new backlog items (bugs found, deferred MINOR findings, follow-ups), pattern candidates to put to the user, plus anything for next iteration's Requirements or Design phase.

Then re-order the backlog and decide:

| Decision | When |
|---|---|
| `CONTINUE` | Criteria are still unverified or must-do backlog items remain, and this iteration made progress. Start the next iteration at Phase 1 or 2 if the retro queued something for them, otherwise at Phase 3. |
| `RELEASE` | Every criterion is verified, every invariant is covered by a test or marked untouched with the reason, and no must-do item remains. |
| `ASK` | A stop condition was hit (see [Limits](#limits)). |

Give the user a one-line status after each iteration, e.g. `Iteration 2: AC-3, AC-4 verified (4/7). Next: permissions slice.` Don't wait for a reply unless the decision is `ASK`.

## Release

1. **Final review and security pass**, launched in one message, each a fresh agent on the whole branch diff against the base:
   - **Final review.** Slice-by-slice review misses what only shows across slices: duplicated helpers, inconsistent naming, leftover scaffolding, a contract one slice changed under another, a pattern applied one way in one slice and another way in the next.
   - **Security pass.** It confirms that every abuse case in the threat model has a mitigation in the code and a test, then looks for what per-slice review can't see, such as an authorization check each slice assumed another would do. Skip it only if `design.md` states the work adds no attack surface. Don't make that call yourself at this point; a tired driver at the end of a long run is the wrong judge of what is sensitive.
2. **Skeptic check.** For each BLOCKER from either agent, launch a fresh-context skeptic (all in one message) with only the claim, the location, the failure scenario and the diff command, and ask it to disprove the finding. It replies `CONFIRMED`, `PLAUSIBLE` or `REFUTED` with evidence. A finder is biased toward its own finding, and a false blocker here costs a whole iteration. Drop refuted findings and list them in the report as checked. If you disagree with a refutation, read the code yourself and decide on the evidence. Findings inside an iteration don't need this, because the engineer can already dispute them.
3. **Full checks and scanners**, one more time.
4. **Findings re-enter the loop.** Confirmed and plausible BLOCKERs, and MAJOR findings, become backlog items and you run another iteration. Release is a phase of the loop, not an exit from it.
5. **Completeness check.** When no finding remains, fill in the Completeness table of the [report](#report), counting from the files: the criteria table in `state.md`, each iteration's completeness table, the reports in `release/`, and the output of step 3. Every criterion needs a named test that passed in step 3's run, every invariant a test or "untouched" with its reason, every abuse case a criterion and a test, every pattern that applied a reviewer result in each slice it applied to, and every BLOCKER a skeptic's verdict. A shortfall is a backlog item and another iteration, as in step 4. It is not a note in `release.md`.
6. When clean, write `release.md`: what changed, the criteria table with the test that verifies each one, the security summary, design decisions worth a reviewer's attention, and known limits.
7. **Gate:** show the summary and ask before pushing or opening a PR. These publish on the user's behalf, so `--auto` doesn't cover them.
8. **After the PR**, CI failures and review comments are feedback like any other: add them to the backlog and run another iteration. The loop ends when the user says the work is done.

## Routing failures back

| Signal | Goes back to |
|---|---|
| Review finding or test failure where the code is wrong | Build, same iteration |
| Test is wrong (engineer disputes it and the tester agrees) | Tester, same iteration |
| Criterion is ambiguous, untestable, or disputed twice | Requirements; ask the user |
| Engineer or reviewer shows the design can't satisfy a criterion | Design, then re-plan the slice |
| Slice still failing after 3 fix rounds | Plan; split it or reorder, and note why in the retro |
| Scanner finding this work introduced | Build, same iteration |
| A `must` pattern broken in the slice | Build, same iteration |
| A pattern can't be followed here, or two patterns conflict | The user. Update the patterns file with the answer, then Design if it changes a contract |
| Security finding that needs a boundary or check the design doesn't have | Design, to update the threat model; add or fix the `[security]` criterion, then re-plan |
| Edge case the requirements and design don't cover (`UNSPECIFIED`) | Requirements; once settled it becomes a criterion or invariant |
| Regression in an earlier slice | Build, with the earlier iteration's file as context |
| CI failure or PR comment after release | Backlog, next iteration |

When a failure routes backwards across phases, leave the unfinished slice uncommitted, record the reason in the retro, and let the next iteration pick it up from the phase the failure points at.

## Limits

Stop and ask the user (`ASK`) when any of these holds. Report the open items and offer concrete options instead of looping further:

- `--max-iterations` is reached.
- An iteration verified no new criterion and closed no backlog item.
- The backlog grew in two consecutive iterations. This usually means the scope is wrong, not the code.
- A requirement contradicts another, or the user's answer changes the goal.
- A check command can't be run in this environment, so verification isn't possible.

## Report

End every run, whether it finished or stopped, with:

```markdown
## SDLC Loop: <work>

**Status:** ✅ Ready to release | ⏸ Stopped: <reason> | 🔁 In progress (resumable)
**Branch:** `<branch>` · **Iterations:** <n> · **Artifacts:** `<dir>`

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
- **Patterns:** <each PAT-n that applied: followed, exception granted (reason), or open finding; patterns captured or proposed during this run; exemplars awaiting confirmation>
- **Languages:** <each language, its reference file or the standard named instead, and the formatter and linter that ran>

### Iterations
- 1: <slice> → <outcome, fix rounds>
- 2: …

### Completeness
| What | Expected | Done | Gap and reason |
|---|---|---|---|
| Criteria verified by a named test that passes on the final commit | 7 | 7 | |
| Invariants verified, or untouched with the reason | 3 | 3 | |
| Abuse cases with a criterion and a test | 4 | 4 | |
| Patterns that applied, with a reviewer result in every slice | 3 | 3 | |
| Iterations with all seven phase sections and a completeness table | 3 | 3 | |
| Agent reports on disk, against agents launched | 19 | 19 | |
| Reports sent back for a missing contract section | — | 2 | |
| Release: final review, security pass, a skeptic per BLOCKER | 2 + 1 | 2 + 1 | |
| Checks and scanners run on the final commit | 5 + 2 | 5 + 2 | static analysis: no tool |

<for a run that stopped early, fill in the rows it reached and write "not reached" in the rest>

### Open items
<unverified criteria, unresolved or disputed findings, deferred MINOR items, assumptions made under --auto>
<branches or edge cases in changed code that no test exercises, and why; coverage of changed code if it was measured>

### Who did what
<role → agent type and model; any escalation, substitution or --models override>
```

Agent output isn't visible to the user, so this report and the per-iteration status lines are all they see. State what wasn't done as plainly as what was.
