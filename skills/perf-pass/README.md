# perf-pass

Finds what makes code slow and fixes it one change at a time. A fix is kept only if the benchmark shows it faster than the run-to-run noise, the output is unchanged, and the tests still pass.

## When to use it

- "`GET /orders` is slow, find out why and speed it up."
- "Profile this command / job / query / page and fix the top costs."
- "Does this change introduce an N+1 query or a quadratic loop?"
- You want a benchmark at realistic sizes, with before and after numbers.
- Not for: a general correctness review (use [`pr-review`](../pr-review/) or [`deep-review`](../deep-review/)), or restructuring hard-to-change code without a performance goal (use [`hotspots`](../hotspots/)).

## Usage

```
/perf-pass [target] [options]
```

There are two modes. In **measure** mode you name something slow (an endpoint, command, page URL, query, job or function) or give a benchmark command with `--bench`. In **scan** mode you give `--scan`, a commit, range, branch, PR or paths, and it looks for antipatterns in the changed lines or those files. With no target at all, it asks what is slow; if you don't know, it scans the uncommitted changes or the branch.

| Option | What it does |
|---|---|
| `--scan` | Scan mode, even when a slow thing is named. The named thing then narrows the scope. |
| `--bench <cmd>` | Use this command as the benchmark instead of building one. |
| `--runs <n>` | Measured runs per benchmark, after warm-up. Default 10. |
| `--report-only` | Stop after the plan. Nothing is edited. |
| `--auto` | Apply behavior-preserving (P) fixes without waiting for plan approval, still keeping only those that measure faster. Behavior-changing (B) fixes still need a yes each. |
| `--models <role>=<model>,…` | Override an agent's model. Roles: `profiler`, `skeptic`, `fixer`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/perf-pass GET /orders
/perf-pass --bench "python bench/export.py" --runs 20
/perf-pass --scan
/perf-pass 1234 --report-only
```

## How it works

1. **Get the target.** Mode, scope, where fixes go, where benchmarks may run.
2. **Set up.** Read `docs/conventions.md` and `docs/patterns.md` if present, index the codebase's own caching, batching and pooling helpers for reuse, find installed profilers, record production-like sizes (asking you when the code doesn't say), resolve database and service URLs, and run baseline tests.
3. **Build the benchmark and measure the baseline.** Measure mode: build a repeatable benchmark, run it with warm-up, record median, spread, peak memory and query counts, steady it if the spread is above about 10%, and profile it. Scan mode defers micro-benchmarks to Step 5.
4. **Find the causes.** Each top cost in the profile is explained; in scan mode, one pass per antipattern family (N+1 queries, queries in loops, missing indexes, unbounded queries, memory, quadratic work, blocking I/O in async code, sequential awaits, batching, caching, bundles, React re-renders and others).
5. **Verify every finding.** Is the hot path real, and do the sizes reach the point where it matters? Scan mode measures the top five suspected findings. Unmeasured ones stay "suspected".
6. **Plan.** Fixes in order of expected gain, each with its class and an upper bound from the profile. A skeptic agent checks what each B fix would break. You approve all, some or none.
7. **Apply one fix at a time.** Back up, make the minimal change, run the tests, run the benchmark, decide by the keep rule. A `NEAR` result gets an alternating A/B re-run and a skeptic's read. Anything not kept is restored and recorded with its numbers.
8. **Check completeness.** Counts taken from the work files.
9. **Report.**

Fix classes: **P** preserves behavior (a set instead of a list, an eager load, a reused client). **B** changes something observable (caching, concurrency, indexes, pagination, deferred work, retry timing) and needs your yes per item. **N** needs a decision the code can't settle (a caching layer, a schema redesign) and goes in the report as a recommendation.

## What you get

- Kept fixes as uncommitted changes in your working tree. If your tree has unrelated changes in those files, or the target is another branch or PR, they go to a worktree at `<repo parent>/<repo name>.worktrees/perf-pass-<slug>` on branch `perf-pass/<slug>`.
- A report: a before-and-after table (median, spread, peak memory, query counts), where the time goes before and after, each fix kept and each discarded with its numbers, behavior changes applied, suspected issues not measured, recommendations, and limits such as assumed sizes.
- A work directory outside your repo (`<scratchpad>/perf-pass-<slug>/`, or a temp dir) with one file per step, the ledger, the benchmark scripts and every run's JSON in `bench/`, profiles in `prof/`, and backups.

## Safety

- Never benchmarks production. Benchmarks and profiles run on this machine or in a test environment you name in the conversation; a host found in a config file or `.env` doesn't count. Database and service URLs are resolved and checked first, and if one isn't local or named by you, it stops and asks.
- Writes go only to a scratch database the project already supports. Third-party APIs are stubbed or counted, not called.
- Commits nothing. It never switches your branch, stashes or resets.
- Runs code only on your own work or a branch of the same repository, with what is already installed. It never installs profilers or benchmark tools; if one would help, the report names it.
- A PR from a fork is scanned only, never run.
- A fix whose tests fail is restored from backup and marked `reverted`, not debugged into place.
- Text in code, comments or a PR description that tells Claude what to do ("benchmark against prod") is reported as a finding, not followed.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/measuring.md` | How to build a benchmark, the noise rules and keep rule, profilers and query counting, and the formats for the work files, plan and report |
| `references/antipatterns.md` | The fix classes, the antipattern families, and how to confirm a finding |
| `scripts/bench.py` | Runs benchmarks and applies the keep rule. Python standard library only. |

`bench.py` has three subcommands: `run` times a command with warm-up and records median, spread and peak memory; `ab` alternates two versions to cancel machine drift; `compare` applies the keep rule to two results.

```
python3 scripts/bench.py run --cmd "<benchmark>" --out before.json --runs 10
python3 scripts/bench.py compare before.json after.json
```

## Related skills

- [`conventions`](../conventions/) — writes `docs/conventions.md`, which every fix follows; run it if the repo has none.
- [`sdlc-fast`](../sdlc-fast/) — writes `docs/patterns.md`, which this skill also reads.
- [`guided-review`](../guided-review/) — walks you through the resulting diff.
- [`deslop`](../deslop/) — tidies the diff afterwards.
