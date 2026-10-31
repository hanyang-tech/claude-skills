# claude-skills

Skills for [Claude Code](https://claude.com/claude-code) that review, clean up and strengthen code, and take work from an idea to a release-ready branch. Each skill is a folder under `skills/` with a `SKILL.md` that Claude follows and a `README.md` for people.

## Skills

### Build

| Skill | What it does |
|---|---|
| [`sdlc-loop`](skills/sdlc-loop/) | Runs the whole lifecycle as an iterative multi-agent loop (requirements, design, plan, build, review and test, integrate, retro) until every acceptance criterion is verified. |
| [`sdlc-fast`](skills/sdlc-fast/) | The same loop tuned for wall-clock time: parallel lanes in worktrees, targeted tests, delta fix rounds. |

### Review

| Skill | What it does |
|---|---|
| [`deep-review`](skills/deep-review/) | Reconstructs a change's intent, reviews it through independent lenses, and reports only verified bugs and risks. |
| [`pr-review`](skills/pr-review/) | Works out what a PR does from the code, then asks: could it be simpler, which cases does it miss, does it fit the codebase? |
| [`guided-review`](skills/guided-review/) | Guides you through reviewing a change unit by unit, most important first, so you read every hunk and see the problems in it. |

### Improve

| Skill | What it does |
|---|---|
| [`deslop`](skills/deslop/) | Finds and removes AI slop (narrating comments, defensive overkill, reinvented helpers, fake implementations) judged against the codebase's own style. |
| [`conventions`](skills/conventions/) | Measures how the codebase is actually written and records it in `docs/conventions.md`, with counts and exemplars. |
| [`test-strength`](skills/test-strength/) | Mutation-tests the code and writes tests, from the requirements, for the bugs the tests miss. |
| [`hotspots`](skills/hotspots/) | Ranks the files that cost the most to change and refactors them in small, behavior-preserving steps. |
| [`error-paths`](skills/error-paths/) | Tests what happens on timeouts, bad responses, partial failure, races and clock edges, and fixes the handling. |
| [`dep-hygiene`](skills/dep-hygiene/) | Cleans up vulnerable, unused, missing, overlapping and outdated dependencies, and internal import boundaries. |
| [`perf-pass`](skills/perf-pass/) | Benchmarks, profiles and fixes slow code, keeping only changes that measure faster with the same output. |

## How they behave

- **Nothing is committed or pushed** unless you ask.
- **You approve a plan before anything is edited.** Behavior-changing fixes need a yes each.
- **Every finding is verified** against the code before it is reported or fixed.
- **Fixes are applied in small batches** with tests before and after, and a batch that breaks something is reverted.
- **Work files go to a scratch directory**, not your repository. Each run ends with a report.
- **Nothing is installed.** Tests and tools run only on your own code, with what is already installed.

## Install

Link the skills you want into your personal skills folder:

```bash
git clone git@github.com:hanyang-tech/claude-skills.git
```

```bash
for s in claude-skills/skills/*/; do ln -s "$PWD/$s" ~/.claude/skills/; done
```

Or link one at a time:

```bash
ln -s "$PWD/claude-skills/skills/deslop" ~/.claude/skills/deslop
```

Then call a skill with `/<name>` in Claude Code, or ask for what it does in your own words.
