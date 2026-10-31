# sdlc-loop

Takes a feature or sizeable change from idea to a reviewed, tested, release-ready branch by going round the development lifecycle in iterations, with a separate agent for each role. You end up with local commits on a branch, a criteria table showing which test verifies each requirement, and a PR description that waits for your go-ahead.

## When to use it

- "Build this feature end to end, from requirements to a PR."
- The requirements or design still have to be settled before anyone writes code.
- The work spans more than one slice and you want each slice built, reviewed and tested before the next one starts.
- You want an engineer, a reviewer and a tester that don't share context, so the code is judged against the criteria and not against its author's story.
- Not for: a small change where requirements and design are already clear and one build-and-review pass will do. To review a change that already exists, use [`deep-review`](../deep-review/). If wall-clock time matters more than strict one-slice-at-a-time order, use [`sdlc-fast`](../sdlc-fast/).

## Usage

```
/sdlc-loop [description of the work] [options]
```

With no description it uses the task from the conversation, and asks if there is none.

| Option | What it does |
|---|---|
| `--spec <path>` | A requirements, ticket or design file to treat as the starting requirements |
| `--max-iterations N` | Iteration limit before it stops to ask. Default 5 |
| `--auto` | Don't pause at the requirements and design gates; assumptions are recorded and flagged in the report. Pushing and opening a PR still need you |
| `--dir <path>` | Work directory. Default `docs/sdlc/<slug>/` |
| `--patterns <path>` | File holding your implementation patterns. Default: the one it finds, else `docs/patterns.md` |
| `--models <role>=<model>,…` | Override a role's model. Roles: `architect`, `engineer`, `reviewer`, `tester`, `final-reviewer`, `security-reviewer`, `skeptic`. Values: `sonnet`, `opus`, `fable` |

Examples:

```
/sdlc-loop add CSV export to the reports page
/sdlc-loop --spec docs/tickets/billing-v2.md --max-iterations 3
/sdlc-loop --auto --models architect=fable,security-reviewer=fable add team-level permissions
```

## How it works

Setup first: create the branch (`sdlc/<slug>` if you are on the default branch), record the check commands, security scanners (with a baseline run), languages and patterns file, assign agents to roles, and create the work directory. If `state.md` already exists in the work directory, it resumes from there.

Each iteration delivers one thin slice:

1. **Requirements** - numbered acceptance criteria (`AC-n`) and invariants (`INV-n`), each testable. Gate: you approve them.
2. **Design** - the architect writes the approach, contracts, threat model and the patterns that apply. Abuse cases become `[security]` criteria. Gate: you approve.
3. **Plan** - pick the next slice from the backlog and map it to criteria.
4. **Build** - the engineer implements only that slice and its unit tests.
5. **Verify** - a reviewer and a tester, started fresh and run in parallel, never see the engineer's summary. Up to 3 fix rounds.
6. **Integrate** - run the full suite and scanners, count what was expected against what was done, commit locally.
7. **Retro** - record what was delivered and learned, then decide `CONTINUE`, `RELEASE` or `ASK`.

Phases 1 and 2 are revisited only if the retro queued something for them.

Release runs a final whole-branch review and a security pass, then a skeptic tries to disprove each BLOCKER. Confirmed findings go back into the loop as another iteration. When clean, it writes `release.md` and asks before pushing.

Code is held to your patterns first (`PAT-n`), then project rules, then the surrounding code, then a per-language reference. Patterns are captured from you as the work goes, and only after you confirm them. The loop stops and asks you if the iteration limit is reached, an iteration verifies nothing new, the backlog grows two iterations running, requirements contradict, or a check can't be run.

Models: `opus` for design, per-slice review, release passes and skeptics; `sonnet` for the engineer and tester. `fable` is used only if you pass it in `--models`. A stuck item gets a fresh `opus` engineer for the third fix round.

## What you get

- Local commits on the branch, one per passing iteration, naming the criteria covered.
- The work directory (`docs/sdlc/<slug>/` by default): `state.md`, `requirements.md`, `design.md`, `backlog.md`, one file per iteration with its agent reports, `release/` and `release.md`.
- `docs/patterns.md` (or your `--patterns` file), updated with patterns you confirmed. This one lives in the project, not the work directory.
- A final report with the criteria table, security summary, a completeness table counted from the files, open items, and which agent and model played each role.

## Safety

- Nothing is pushed and no PR is opened without your go-ahead. `--auto` does not cover this.
- If the working tree has uncommitted changes, it asks whether they belong to this work and stages only files the work touched.
- It does not install new tools without asking; a missing scanner category is reported as `none`.
- Reviewers, the security reviewer and skeptics are read-only. The tester edits test files only.
- Existing patterns are never edited or dropped without asking.
- Existing code that breaks a standard is a backlog item at most; slices are not widened to fix it.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/roles.md` | Briefs, hand-over lists and output contracts for each role, plus the contract check |
| `references/templates.md` | Templates for the work-directory files and the patterns file |
| `references/languages/python.md` | Python tooling, idioms, pitfalls and testing conventions |
| `references/languages/typescript.md` | The same for TypeScript and JavaScript |
| `references/languages/_template.md` | Starting point for adding another language |

## Related skills

- [`sdlc-fast`](../sdlc-fast/) - the same lifecycle tuned for wall-clock time, with parallel lanes.
- [`conventions`](../conventions/) - measures how a codebase is actually written; its output can seed the patterns file.
- [`deep-review`](../deep-review/) - a standalone review of a finished change.
