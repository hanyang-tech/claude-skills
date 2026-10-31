# sdlc-fast

Takes a feature or sizeable change from idea to a reviewed, tested, release-ready branch, like [`sdlc-loop`](../sdlc-loop/), but organized to save wall-clock time. Independent slices are built in parallel, and each check runs where it is cheapest to be complete. You end up with local commits on a branch, a criteria table showing which test verifies each requirement, a timing breakdown, and a PR description that waits for your go-ahead.

## When to use it

- "Build this end to end, and do it quickly."
- The work splits into several slices that don't touch the same files, so they can be built side by side.
- sdlc-loop worked but was too slow: serial slices, repeated full verify rounds, full test suites run again and again.
- You want to see where the time went (every phase and agent is timed).
- Not for: a small change with clear requirements (one build-and-review pass is enough), or reviewing code that already exists ([`deep-review`](../deep-review/)).

## Usage

```
/sdlc-fast [description of the work] [options]
```

With no description it uses the task from the conversation, and asks if there is none.

| Option | What it does |
|---|---|
| `--spec <path>` | A requirements, ticket or design file to treat as the starting requirements |
| `--max-iterations N` | Iteration limit before it stops to ask. Default 5. An iteration may carry several lanes |
| `--lanes N` | Most slices built in parallel per iteration. Default 3, or 1 when checks can't run in two worktrees at once |
| `--verify auto\|full\|light` | `auto` (default) uses light verify for slices that qualify; `full` always uses a reviewer and a tester; `light` is a preference only, since a slice that doesn't qualify still gets full verify |
| `--auto` | Don't pause at the requirements and design gates; assumptions are recorded and flagged in the report. Pushing and opening a PR still need you |
| `--dir <path>` | Work directory. Default `docs/sdlc/<slug>/` |
| `--patterns <path>` | File holding your implementation patterns. Default: the one it finds, else `docs/patterns.md` |
| `--models <role>=<model>,…` | Override a role's model. Roles: `architect`, `engineer`, `reviewer`, `tester`, `verifier`, `final-reviewer`, `security-reviewer`, `skeptic`. Values: `sonnet`, `opus`, `fable` |

Examples:

```
/sdlc-fast add CSV export, saved filters and an audit log to the admin area
/sdlc-fast --spec docs/tickets/search-rewrite.md --lanes 2
/sdlc-fast --verify full --models architect=fable add SSO login
```

## sdlc-fast or sdlc-loop

Both run the same phases, keep the same state on disk, and require every acceptance criterion to be verified by a passing test before release. The differences are about time:

| | sdlc-loop | sdlc-fast |
|---|---|---|
| Slices | One per iteration | Up to `--lanes` independent slices at once, each in its own git worktree |
| Fix rounds | The same reviewer is continued; the tester re-runs the full suite | Delta rounds: only the fix diff is re-read, only failed or affected tests re-run |
| Test runs | The tester runs the full suite each round; Integrate runs it again | Targeted tests in verify; the full suite once per iteration |
| Small slices | Always a reviewer and a tester | One light verifier if the slice qualifies |
| MINOR findings | Not part of the fix list | Go to the backlog and `release.md`, and never start a round or an iteration |
| Flaky tests | No special rule | Rerun up to 20 times or 5 minutes, then quarantined or sent to the engineer |
| Design changes | Sent to the architect; contract, data-model and trust-boundary changes go through your gate | Only contract, data-model, trust-boundary and dependency changes go to the architect and you; the driver notes the rest |
| Timing | Not recorded | Every phase and agent is timed |

Pick sdlc-loop for the plainest process, one slice at a time. Pick sdlc-fast when wall-clock time matters, especially when the slices are independent. When checks can't run in two worktrees at once, lanes default to 1; the other time savers still apply.

## How it works

1. **Requirements** - numbered acceptance criteria and invariants, each testable. Gate: you approve.
2. **Design** - the architect writes the design, threat model, patterns per component and the dependencies between components. Abuse cases become `[security]` criteria.
3. **Plan** - choose independent slices as lanes, set up a worktree per lane.
4. **Build** - one engineer per lane, followed by a round commit.
5. **Verify** - full verify (reviewer and tester) or light verify (one verifier) per lane, as soon as its build finishes. Up to 3 fix rounds per lane.
6. **Integrate** - per lane: checks, scanners, completeness count, squash and merge. Then the full suite once on the merged result.
7. **Retro** - delivered, learned, time, queued, and a `CONTINUE`, `RELEASE` or `ASK` decision.

Release runs a final review and a security pass on the whole branch, then a skeptic per BLOCKER. It reuses the last full-suite result if the branch hasn't moved since.

A lane qualifies for light verify only if it is under about 200 changed lines, has no `[security]` criterion or trust-boundary change, changes no shared contract, data model or dependency, and every pattern it applies already has a confirmed exemplar. A BLOCKER or `security:` finding from the verifier sends the lane to full verify.

Models and patterns work as in sdlc-loop: `opus` for judgment, `sonnet` for volume (the verifier too), and `fable` only through `--models`.

## What you get

- Local commits on the branch, one per merged lane, naming the criteria covered.
- The work directory: `state.md`, `requirements.md`, `design.md`, `backlog.md`, one file per iteration and per lane, agent reports, `release/` and `release.md`.
- `docs/patterns.md` (or your `--patterns` file), updated with patterns you confirmed.
- A final report with the criteria table, security summary, a time table, a completeness table and open items, including deferred MINORs and quarantined flaky tests.

## Safety

- Nothing is pushed and no PR is opened without your go-ahead. `--auto` does not cover this.
- Lane worktrees live outside the repo, in `<repo parent>/<repo name>.worktrees/`, and are removed after merge.
- If the working tree has uncommitted changes, it asks whether they belong to this work.
- It does not install new tools without asking.
- If lanes conflict outside an append-only registration point, the merge is aborted and the later lane is rebased and re-verified.
- On resume, a missing lane worktree means its uncommitted work is lost, so that slice is re-planned.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/roles.md` | Role briefs and output contracts, including the verifier and delta rounds, and the contract check |
| `references/templates.md` | Templates for the work-directory files, lane files and the patterns file |
| `references/languages/python.md` | Python tooling, idioms, pitfalls and testing conventions |
| `references/languages/typescript.md` | The same for TypeScript and JavaScript |
| `references/languages/_template.md` | Starting point for adding another language |

## Related skills

- [`sdlc-loop`](../sdlc-loop/) - the one-slice-at-a-time version of the same lifecycle.
- [`conventions`](../conventions/) - records how a codebase is written; its decided rules can be promoted to the patterns file this skill enforces.
