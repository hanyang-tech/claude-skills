---
name: conventions
description: Work out how a codebase is actually written and record it as a short, evidence-backed conventions doc that people and other skills can follow. Samples the codebase's most established files, extracts conventions across layout, naming, errors, validation, types, logging, config, data access, boundaries, concurrency, dependencies, comments, tests, library choices and git style, then counts how widely each one holds across the whole codebase and marks it established, prevailing or mixed, with exemplars and counter-examples. Asks the user to settle mixed areas and migrations, writes docs/conventions.md with a reuse index of the helpers to use, points CLAUDE.md at it, and proposes lint rules for what a tool can check. Use when the user asks to document, extract, learn or write down a codebase's conventions, style guide, coding standards or house style, wants a CLAUDE.md or conventions file for a repo, or invokes /conventions (options --out, --scope, --update, --auto, --models). Commits nothing.
---

# Conventions

Work out how this codebase is written, prove each convention with counts, and write it down where people and agents will read it.

Target: `$ARGUMENTS`.

The output is one document in the repository, `docs/conventions.md` by default. It is for whoever writes code here next, whether a person, deslop, guided-review or sdlc-fast. It answers "how do we do X here?" with a rule, how widely it holds, a file that shows it, and a file that doesn't.

## Principles

- **Describe what is, not what should be.** A convention is what the code does, counted. What the code ought to do is a recommendation, kept in its own section, or a decision the user makes. The doc never presents a preference as the codebase's practice.
- **Every convention is counted.** "We use custom error types" becomes "custom error types in 34 of 39 modules that raise (`rg …`)". The count decides how strong the convention is. An impression is not a convention.
- **Learn from established code.** Prefer files with many authors, many commits and a long life. Recently added code may be the thing that doesn't follow the conventions yet. When the history is too young to tell, say so and lean on counts and the user.
- **Show, don't describe.** Each convention points at an exemplar (`path:line`) and, where one exists, a file that breaks it. A writer copies from an example faster than from a sentence.
- **Only what a newcomer would get wrong.** Leave out language defaults and anything the formatter enforces. A conventions doc that restates PEP 8 gets skimmed, and the rules that matter get skipped with it.
- **Mixed is a finding, not a rule.** Where the codebase disagrees with itself, the doc says so, and the user decides. A coin-flip written as a rule makes every later review argue about it.
- **Short.** The doc is read before every task. Aim for under 250 lines, and put the detail in the evidence files, not the doc.

## Working method

Each step writes a file to `<work>` before the next one starts, and later steps work from the files.

**Work directory.** `<work>` is `<scratchpad>/conventions-<repo name>/` when the session has a scratchpad, else a new temporary directory (`mktemp -d`). The doc itself goes in the repository. Everything else stays in `<work>`.

```
<work>/
├── steps.md          # the step list, ticked as each file is written
├── 1-scope.md        # repo, scope, languages, written rules found, tools, mode
├── 2-sample.md       # the files studied, why, and how reliable the history is
├── 3-candidates.md   # candidate conventions per topic, with examples
├── 4-measured.md     # each candidate counted across the scope, with the command
├── 5-decisions.md    # mixed areas and migrations, and what the user decided
├── 6-coverage.md     # the completeness check
└── doc-draft.md      # the doc before it is written to the repository
```

**Step list.** Before Step 1, write `steps.md` with steps 1 to 8 and their files. If the session has a task list (TaskCreate or TodoWrite), create one task per step. Tick a step only once its file exists. After a context summary, read `steps.md` and `<work>` and carry on from the first unticked step.

**References.**
- Steps 3 and 4 follow [references/topics.md](references/topics.md).
- Steps 6 and 7 follow [references/format.md](references/format.md).
- Read each file in full, in this run, before its first step.
- [scripts/established.py](scripts/established.py) ranks files for Step 2.

## Step 1 — Scope

| Argument / option | Effect |
|---|---|
| *(empty)* | The whole repository. |
| `--scope <dir>` | One package or app in a monorepo. The doc goes in that directory's `docs/` unless `--out` is given. |
| `--out <path>` | Where to write the doc. Default `docs/conventions.md`, or the existing conventions doc if there is one. |
| `--update` | Refresh an existing doc: re-measure every convention, keep its ID, and report what changed. This is the default when the doc already exists. |
| `--auto` | Don't ask about mixed areas. Record them as mixed, and list them in the report. |
| `--models <role>=<model>` | Override an agent's model. Roles: `extractor`, `skeptic`. Values: `sonnet`, `opus`, `fable`. |

Then collect:

- **Languages and layout:** the languages, their file counts, and the top-level areas (apps, packages, services, layers).
- **Written rules:**
  - `CLAUDE.md` (root and nested), `AGENTS.md`, `CONTRIBUTING.md`
  - `docs/patterns.md` (sdlc-fast's user-confirmed patterns)
  - an existing conventions or style doc, ADRs, `.editorconfig`
  - the formatter, linter and type-checker configs, and import-boundary tools
  - These are claims to check against the code, not conventions to copy. A written rule the code ignores is a finding.
- **Tools:** the formatter, linter, type-checker and test runner commands, from the configs, the package scripts, the Makefile and CI.
- **Mode:**
  - Small codebase (under about 30k lines in scope): do Steps 3 and 4 yourself.
  - Larger: use extractor agents per topic group (see Step 3).

Write `1-scope.md` in the format in [references/format.md](references/format.md). Then tell the user in one line what you are studying and where the doc will go.

## Step 2 — Choose what to study

Run:

```bash
python3 <skill dir>/scripts/established.py --repo <repo> [--scope <dir>] --top 5
```

It ranks tracked source files by authors, commits and age, per top-level area, lists recently added files, and warns when the history is too thin to rely on.

From its output pick the **sample**:

- **Three to five files per area and layer.** Handlers, services, data access, models, utilities, CLI, UI components and tests each get their own, so every kind of code is represented.
- **Representative files.** Skip giant legacy files and trivial ones such as `__init__.py` or a re-export index.
- **The shared helpers.** Find the utility modules everyone imports by counting imports (`rg -o "from \S+ import|import \S+|require\(['\"][^'\"]+" | sort | uniq -c | sort -rn | head -40`). These feed the reuse index.
- **About 20 to 40 files** in total, more for a big monorepo.

If the script printed **WEAK HISTORY**, the history can't separate established from new. Pick by area coverage only, and note in `2-sample.md` that conventions will rest on counts and the user's confirmation.

Write `2-sample.md`.

## Step 3 — Extract candidates

Read [references/topics.md](references/topics.md) in full first. For each topic, read the sample with the topic's questions in mind, and write down candidate conventions with two or three example locations each. Write `3-candidates.md` in the topic reference's output contract. A topic where nothing stands out still gets a line, so "nothing found" can be told apart from "not looked at".

**Agent mode.** Split the topics into three or four groups and launch one **extractor** agent per group in one message. Use `general-purpose` agents with `model: sonnet`, since this is pattern work.

Each brief stands on its own. It gives:
- the repository path and the scope
- the path of `2-sample.md`
- the absolute path of `references/topics.md`, to read in full
- the topics the agent owns
- the file to write: `<work>/3-candidates-<group>.md`, in the output contract
- what to reply with: the path, and the candidate count per topic
- that it edits nothing in the repository

Check each result against the contract. If a topic or an example is missing, send the agent back for it.

## Step 4 — Count each one

For every candidate, count how widely it holds across the **whole scope**, not just the sample, following Part 2 of the topic reference:

1. **The denominator.** Count the places where the convention applies, not all files. "Handlers that return errors", not every file.
2. **The count.** Use a search you can show (`rg -c`, `rg -l | wc -l`, an AST query, or the linter). Record the command. When search can't separate the cases, read a random sample of at least 15 sites and say that's what you did.
3. **The strength:**
   - **established:** 80% or more
   - **prevailing:** 60% to 80%
   - **mixed:** under 60%, or two styles with no clear winner
4. **Direction.** Compare files added in the last 90 days with the established files. If new code consistently does it differently, record a **migration**, old → new. That might be intended, or it might be drift.
5. **Exemplar and counter-example.** Pick the clearest file that follows the convention and, if there is one, a file that doesn't.
6. **Written rules.** For each one from Step 1, record whether the code follows it.

**Drop** a candidate that is a language default or enforced by the formatter, unless writers often get it wrong anyway. Instead, the doc's Tools section tells writers to run the tool.

**Skeptics,** in agent mode. For each established convention that sounds like a strong rule, such as "never", "always" or "only", launch a fresh `opus` agent. Give it only the rule and the repository, and ask it to find counter-examples. Launch them together, and adjust the counts to what they find.

Write `4-measured.md`.

## Step 5 — Settle what's mixed

Collect three kinds of question:
- the **mixed** conventions that matter
- the **migrations**
- the **written rules the code ignores**

Rank them by how often a writer will face the choice. Ask the top ones in one round of AskUserQuestion: at most four questions, each offering the more common or newer style first and the other as the second option. Each option shows its count and an exemplar.

Record what the user decided in `5-decisions.md`, with the date. A decided convention is a **rule** in the doc, labelled as decided by the user. Questions not asked stay mixed, and the doc lists them.

With `--auto`, ask nothing. Record each as mixed, and list them in the report.

## Step 6 — Write the doc

Read [references/format.md](references/format.md) in full first. Write `doc-draft.md` in its template:

- tools first
- then conventions by topic, each with ID, strength, rule, count, exemplar and counter-example
- the reuse index
- what's mixed
- migrations
- recommendations
- what tools could enforce

Then cut it:
- Drop conventions a newcomer wouldn't get wrong.
- Merge ones that say the same thing.
- Keep each convention to its lines in the template.
- If the draft runs past about 250 lines, move the lowest-value topics' detail out and leave one line each.

**Update mode.**
- Keep existing IDs and never reuse a dropped one.
- Re-measure every convention.
- Keep any convention the user wrote or decided exactly as written, unless the code now contradicts it. In that case, ask.
- List what changed in the doc's Changes section.

Write the draft to `--out` in the repository. If `CLAUDE.md` exists, add the pointer from the format reference under a `## Conventions` heading, or update the existing one. Change nothing else in it. If there is no `CLAUDE.md`, don't create one. Offer it in the report.

## Step 7 — Check completeness

Count from the files. Write `6-coverage.md`:

```
| What | Count | Has to hold |
|---|---|---|
| Step files | <n> present | all |
| References read in this run | topics.md · format.md | both |
| Areas in scope | <n> · <n> represented in the sample | all |
| Topics | <n> of 15 with a line in 3-candidates | 15 |
| Candidates | <n> → <n> counted, <n> dropped (default/formatter), <n> merged | in = the sum |
| Counted with a command | <n> · by sampled reading <n> | every one has one or the other |
| Exemplars | <n> conventions · <n> with an exemplar that exists at that path:line | equal |
| Written rules | <n> found · <n> checked against the code | equal |
| Mixed and migrations | <n> · <n> decided · <n> left mixed and listed | sum |
| Doc length | <n> lines | about 250 or less |
| Agents | inline, or <n> extractors · <n> skeptics · <n> sent back | |
```

Check every exemplar path and line still exists, since a broken pointer is worse than none. If a row doesn't hold, go back to its step, do the work and recount.

## Step 8 — Report

Tell the user:

- where the doc is and how long it is
- counts: established, prevailing and mixed conventions, and decisions made
- the reuse index size
- the most important conventions, three to five, one line each
- written rules the code ignores
- migrations in progress
- what's still mixed
- the lint rules proposed
- whether the history was too thin to rely on
- what changed, in update mode

Commit nothing.

## After the report

Offer these, but don't do them unasked:

- **Promote decided and established conventions to `docs/patterns.md`**, as `PAT-n` entries in sdlc-fast's format, for the ones the user confirms as rules. That's the file sdlc-fast enforces.
- **Add the proposed lint rules** to the linter config, run the linter, and show how many existing violations each rule finds before turning it on.
- **Run `/deslop --families DRIFT`** on recent code, to bring it in line with the conventions.
- **Create `CLAUDE.md`** with the pointer, if there isn't one.
- **Commit the doc.**
- **Refresh it later** with `/conventions --update`.
