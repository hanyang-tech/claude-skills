# Measuring

Part 1 is how to build the benchmark (Step 3, and Step 5's micro-benchmarks). Part 2 is noise and the keep rule (Steps 3, 5 and 7). Part 3 lists the profilers and query counters per ecosystem (Steps 2 to 5). Part 4 has the output contract of every work file from Step 2 to the report.

## Contents

- Part 1 — The benchmark
- Part 2 — Noise and the keep rule
- Part 3 — Profilers and query counting
- Part 4 — Formats

---

## Part 1 — The benchmark

A benchmark is one command that exercises the slow thing the way production does, prints the same output every run, and takes long enough to measure: aim for a run of 100 ms to a few seconds. Shorter, and process start-up and timer noise dominate. Longer, and ten runs take too long to repeat after every fix.

**What goes into it**

1. **The entry point the user named.** Call the endpoint, run the command, load the page, execute the query, invoke the job or the function, the same way production does. Benchmark the whole path first; narrow to a function only when the profile points there.
2. **Realistic sizes.** Use the production-like volumes from `2-setup.md`: rows per table, items per request, payload size, concurrency. A benchmark at fixture size hides every O(n²) and N+1.
3. **Data set-up outside the timing.** Seed with the project's own factories, fixtures or seed scripts, into the scratch database. Set-up runs once before the runs, not inside them.
4. **A stated cache state.** Warm (the second request against a running server, the usual case) or cold (a fresh process, a first page load). Say which, and keep it the same for every measurement.
5. **External calls stubbed.** Replace third-party APIs with the project's existing stubs or recordings (`responses`, `respx`, `vcrpy`, `nock`, `msw`, `httptest`, `WireMock`, `webmock`), with a fixed latency if the real latency matters to the finding. Never time a third-party service.
6. **An output check.** The benchmark prints its result, or a digest of it: the response body, the row count and a checksum, the file written. `scripts/bench.py` hashes stdout, so every run and every fix can be checked for the same output. A faster run with a different output is a bug, not a speed-up. If the output has timestamps or random ids, print a normalized digest instead.
7. **In-process timing when start-up dominates.** Time the body inside the program and print `BENCH ms=<value>`. Print counters the same way: `BENCH queries=<n>`, `BENCH calls=<n>`. `scripts/bench.py` records each as its own metric.

**Where it lives.** By default in `<work>/bench/`, as a small script that imports or calls the project's code. If the user wants the benchmark kept, write it as a bench test in the project's own style instead, and it becomes part of the diff:

| Ecosystem | In `<work>` | Kept in the project, if the project uses it |
|---|---|---|
| Python | a script with `time.perf_counter()` around the call, run in the project's environment (`uv run`, `poetry run`, the venv) | `pytest-benchmark` (`benchmark` fixture), `asv` |
| JS / TS | a `.mjs` script with `performance.now()`, using the project's build output or `tsx` / `ts-node` if installed | `vitest bench`, `tinybench`, `benchmark.js` |
| Go | a `_test.go` file kept in `<work>`, copied next to the package only while it runs and removed after, or `go test -run '^$' -bench <Name> -benchmem -count <n>` on an existing benchmark | a `BenchmarkXxx(b *testing.B)` beside the package's tests |
| Rust | an example binary or a test with `std::time::Instant`, built with `--release` | `criterion` in `benches/`, `cargo bench` |
| JVM | a `main` with `System.nanoTime()` and enough warm-up iterations for the JIT | JMH |
| Ruby | a script with `Process.clock_gettime(Process::CLOCK_MONOTONIC)` under `bundle exec` | `benchmark-ips` |
| HTTP endpoint | `curl -s -o /dev/null -w '%{time_total}\n'` against the local server, or `oha`, `hey`, `wrk`, `ab` if installed, with low concurrency | the project's load-test tool if it has one (k6, Locust), against local only |
| SQL | `EXPLAIN (ANALYZE, BUFFERS)` (Postgres), `EXPLAIN ANALYZE` (MySQL 8), `EXPLAIN QUERY PLAN` plus timing (SQLite), on the scratch database | — |
| Web page | Lighthouse if installed (`npx --no-install lighthouse <local url> --output=json`), or the built-in browser reading `performance.getEntriesByType('navigation')`, `'resource'`, `'longtask'` and `'largest-contentful-paint'` | Lighthouse CI if the project has it |
| Build or bundle size | the build's own size report, `source-map-explorer` or `rollup-plugin-visualizer` if installed | `size-limit` if the project has it |

Build compiled code in release mode (`--release`, `-O2`, production `NODE_ENV`) for the benchmark, unless the user's slow thing is the debug build.

**Running it.** Use `scripts/bench.py` for anything that is a command:

```bash
python3 <skill dir>/scripts/bench.py run --cmd "<benchmark command>" --cwd <repo or worktree> \
  --runs <n> --warmup 2 --out <work>/bench/baseline.json
python3 <skill dir>/scripts/bench.py compare <work>/bench/baseline.json <work>/bench/fix-1.json [--metric ms]
```

`hyperfine` (if installed) is fine for commands too: `hyperfine --warmup 2 --runs <n> --export-json <file> '<cmd>'`. Use `go test -count`, criterion or JMH output directly when the benchmark is written in them, and record the same statistics by hand. Use more warm-up for JIT runtimes (JVM, Node, PyPy): 5 or more runs, or until the times stop falling.

**Micro-benchmarks** (scan mode, Step 5) follow the same rules on a smaller scale: the function or query alone, at the realistic size and at 10× that size, to show how the cost grows. Two sizes tell you more than one: a cost that grows 10× with 10× the input is linear, 100× is quadratic.

**Never run two benchmarks at once,** and never while agents are running or a build is going. Each steals CPU from the other.

---

## Part 2 — Noise and the keep rule

**Statistics.** For each metric record the median, the 25th and 75th percentiles, min and max over the measured runs. The **relative spread** is `(p75 − p25) / median`. Use the median, not the mean: one slow run from a background job shouldn't move the result.

**Noisy baseline.** If the baseline's spread is above about 10%, fix the benchmark before measuring anything else:
- make each run longer (more iterations, a larger input), or time in-process with `BENCH ms=`
- take I/O you don't mean to measure out of the timing
- check what else is running (`uptime` for load average, the heaviest processes in `ps -Ao pcpu,comm -r | head`) and tell the user if something heavy is
- on a laptop, note whether it is on battery (`pmset -g batt` on macOS)

Don't change system settings (CPU governor, turbo, process priority) to quiet the machine; tell the user what you saw instead. If the spread stays high, carry on with the higher threshold the rule gives, and say so in the report.

**The keep rule.** A fix is kept only when all of these hold:

1. **Faster beyond the noise:** the new median beats the before median by more than `max(5%, 2 × the before's relative spread)`. The "before" is the last kept state, measured in the same sitting: the baseline for the first fix, the previous kept fix's "after" for the next one.
2. **The same output:** the output hash matches the before's.
3. **Tests pass:** no new failures against the Step 2 baseline.
4. **No hidden cost:** peak memory not worse beyond the same rule. A fix that is faster but uses more memory beyond the noise is a tradeoff, shown to the user before it is kept.

`bench.py compare` prints the verdict:

| Verdict | Meaning | What to do |
|---|---|---|
| `BETTER` | Gain above 1.5× the threshold | Keep, if the output and tests hold. |
| `NEAR` | Gain between the threshold and 1.5× of it | Re-measure with `bench.py ab`, 2× the runs, alternating before and after (below). Keep only if the re-run says `BETTER` or `NEAR` again, and the skeptic in Step 7 finds the gain real. |
| `NO GAIN` | Within the noise | Revert, record as discarded with the numbers. |
| `WORSE` | Slower beyond the noise | Revert, record as discarded with the numbers. |
| `UNSTABLE` (extra line) | The after's spread is more than twice the before's | Re-run before deciding. |

**Counts are exact.** Query counts, call counts and allocation counts that are identical in every run are compared exactly: fewer is better, with no threshold. A fix kept on a count alone (an N+1 fix measured against a local database, where each query costs little) must still not be slower beyond the noise, and the report says its time gain at production latency is projected from the count, not measured.

**Alternating re-runs.** Machine drift (another process starting, thermal throttling) moves a whole block of runs. Alternating cancels it:

```bash
python3 <skill dir>/scripts/bench.py ab --cmd "<benchmark>" --cwd <repo> \
  --setup-a "cp -R <work>/backup/fix-<n>/. <repo>/ && <build if needed>" \
  --setup-b "cp -R <work>/after/fix-<n>/. <repo>/ && <build if needed>" \
  --runs <2n> --warmup 2 --out-a <work>/bench/fix-<n>-ab-before.json --out-b <work>/bench/fix-<n>-ab-after.json
```

It ends with the after version in place. Use the same command for the final before-and-after headline in Step 7 when the original can be rebuilt cheaply.

---

## Part 3 — Profilers and query counting

Use only what is installed. Check with `command -v <tool>`, the project's dependency manifest and lockfile, and the runtime's built-ins. If nothing fits, fall back to timing sections with `BENCH` lines around the suspect calls, and name the profiler that would have helped in the report. Write every profile to `<work>/prof/`.

| Ecosystem | CPU profile | Reading it | Memory |
|---|---|---|---|
| Python | `py-spy record -o <work>/prof/before.speedscope.json -f speedscope -- <cmd>` (no code change, sees native frames); `python -m cProfile -o <work>/prof/before.pstats <script>` (built in); `scalene --cli --json --outfile <file> <script>` | `py-spy top`; `python -c "import pstats; pstats.Stats('<file>').sort_stats('cumulative').print_stats(30)"`, then `'tottime'` | `tracemalloc` (built in), `memray run`, scalene |
| Node | `node --cpu-prof --cpu-prof-dir=<work>/prof <entry>` (built in); `clinic flame -- node <entry>` | The `.cpuprofile` is JSON: sum `timeDeltas` by node to get self time per function, or `node --prof` then `node --prof-process isolate-*.log` for a text summary | `--heap-prof`, `process.memoryUsage()` |
| Go | `go test -bench <Name> -cpuprofile <work>/prof/cpu.out -memprofile <work>/prof/mem.out`; `net/http/pprof` if the server already exposes it locally | `go tool pprof -top -cum <bin> <work>/prof/cpu.out`, `-list <func>` for lines | `-benchmem`, `go tool pprof -sample_index=alloc_space` |
| Rust | `cargo flamegraph` if installed; `perf record -g` then `perf report --stdio` (Linux); `samply record` if installed; `sample <pid> 10` (macOS, built in) | the text reports; flamegraph SVG for the user | `dhat`, `heaptrack` if installed |
| JVM | async-profiler (`asprof -d 30 -e cpu -o flat <pid>`); JFR, built into JDK 11+ (`-XX:StartFlightRecording=duration=60s,filename=<work>/prof/rec.jfr`) | `jfr print --events jdk.ExecutionSample <file>`, `jfr summary`; async-profiler's flat output | JFR allocation events, `-e alloc` |
| Ruby | `rbspy record --format speedscope -- <cmd>`; `stackprof` if bundled (`StackProf.run(mode: :wall, raw: true, out: …)`) | `stackprof <file> --text --limit 30` | `memory_profiler` if bundled |
| .NET | `dotnet-trace collect`, `dotnet-counters` if installed | `dotnet-trace convert --format speedscope` | `dotnet-counters`, `dotnet-gcdump` |
| Native, any | `sample <pid> <seconds>` (macOS), `perf` (Linux) | text call tree | `/usr/bin/time -l` (macOS), `/usr/bin/time -v` (Linux) for peak RSS |
| Web page | The built-in browser against the local dev or preview build: `performance` entries, a `PerformanceObserver` for `longtask` and `largest-contentful-paint`; Lighthouse if installed | the trace's long tasks and the scripts behind them | `performance.memory` (Chrome) |
| React | The React Profiler (`<Profiler onRender>`) in a local build, or `why-did-you-render` if installed | commits and render durations per interaction | — |

**Reading a profile.** List the top frames by inclusive time until about 80% of the time is covered, or the top ten, whichever is first. For each: the function and `path:line`, self and inclusive share, and what it is doing. Library frames count: the question is which call in the project's code led there. Group frames that are one cost (twenty ORM frames under one `for` loop are one N+1).

**Counting queries and calls.** Count in a test or script that runs the target at size n and 10n against the scratch database:

| Stack | How to count |
|---|---|
| Django | `with CaptureQueriesContext(connection) as ctx: …; len(ctx)`, or `assertNumQueries` |
| SQLAlchemy | `event.listen(engine, "before_cursor_execute", lambda *a: counter.append(1))` |
| Rails | `ActiveSupport::Notifications.subscribed(cb, "sql.active_record") { … }`; `assert_queries_count` (Rails 7.1+) |
| Prisma | `new PrismaClient({ log: [{ emit: "event", level: "query" }] })` and `prisma.$on("query", …)` |
| TypeORM, Sequelize, Knex, Drizzle | a custom logger, `logging: fn`, `knex.on("query", …)`, Drizzle's `logger` option |
| Hibernate / JPA | `hibernate.generate_statistics=true`, `Statistics.getPrepareStatementCount()` |
| Go | a `pgx` `QueryTracer`, a GORM callback, or a counting wrapper around the `database/sql` driver |
| Ecto | a `:telemetry` handler on `[:app, :repo, :query]` |
| HTTP calls | the project's HTTP stub records calls (`responses.calls`, `respx` routes, `nock` scopes, `msw` handlers), or a counter on the shared client |

Print the count as `BENCH queries=<n>` so `bench.py` records it.

---

## Part 4 — Formats

**`2-setup.md`**

```
CONVENTIONS: docs/conventions.md <read | none> · docs/patterns.md <read | none> · other: <CLAUDE.md, …>
REUSE INDEX
| Job | Use this | Where |
|---|---|---|
(caching, batching / DataLoader, shared HTTP client, DB pool, task queue, bulk insert, pagination, retry helper)

TOOLS
| Tool | Command | Installed |
|---|---|---|
(benchmark runner, CPU profiler, memory profiler, query counter, test runner, release build, bundle report)

SIZES
| Input | Production-like value | Source: user · fixture · docs · assumed |
|---|---|---|
CALL FREQUENCY: <how often the target runs: per request at <n>/s, nightly, per page load; source>

ENVIRONMENT
Benchmarks run against: <local: what> | <test environment the user named: host>
Database: <scratch database and how the project provides it> · checked: <the resolved URL's host is local or the named test host>
External calls: <stubbed with … | counted, not made>
Machine: <OS, CPUs> · load average <n> · power <AC | battery>

BASELINE TESTS
Command: <…> · <n> passed · <n> failed · <n> skipped · <duration>
Already failing: <test ids, or none>
```

**`3-benchmark.md`**

```
MODE: measure | scan (one line: micro-benchmarks come in Step 5)

BENCHMARK
Measures: <entry point · warm | cold · what one run does>
Command: <exact> · harness: <work>/bench/<file> | <project path>
Input: <sizes and how the data is set up>
Output check: <what is hashed or compared>
Runs: warm-up <w> · measured <n> · runner <bench.py | hyperfine | go test -count | …>

BASELINE
| Metric | Median | p25–p75 | Rel. spread | Min | Max |
|---|---|---|---|---|---|
| wall ms | | | | | |
| peak RSS MB | | | | | |
| queries / calls | | | | | |
Keep threshold: max(5%, 2 × <spread>) = <x>%
Noise: ok | high: <what was tried, what remains>
Raw: <work>/bench/baseline.json

PROFILE (<tool>, <work>/prof/<file>)
| Rank | Frame (path:line) | Self % | Incl. % | What it is doing |
|---|---|---|---|---|
Covered: top <n> frames = <x>% of time
```

**`4-findings.md`** (or `4-findings-<group>.md` from a scanner)

```
SOURCE: profile | scan · FILES: <every file owned, one per line, in scan mode>

FAMILY PASSES
| Family | Files checked | Findings |
|---|---|---|
| N1 | 14 | 2 |
| QLOOP | 14 | 0 |
(every family in the catalog; in measure mode, the families checked against the hot frames)

FINDINGS
### PERF-<n> <FAMILY> <one-line claim>
- Where: <path:line-line>
- What: <the code, quoted briefly>
- Cost: <x% of the profile (frame rank <n>) | suspected>
- Matters at: <size in the target's units, and the arithmetic>
- Evidence: <profile frames, call sites, schema, loop bounds>
- Fix: <the change, concretely> · Class: P | B | N
- Measure with: <the benchmark | a micro-benchmark at n and 10n | a query count | EXPLAIN>

MINOR: <profile frames under 5%, one line each, or none>
```

**`5-verification.md`**

```
| ID | Claim | Hot path | Assumption checked | Measured how | Result | Status | Class |
|---|---|---|---|---|---|---|---|
| PERF-1 | N+1 on order lines | 41% of wall time | ~200 lines per order (user) | queries n=20: 22 · n=200: 202 | linear | confirmed | P |
| PERF-4 | regex compiled per row | not in profile | — | — | — | dropped: not hot | — |
| PERF-7 | sequential awaits | unknown | — | not measured: below top five | — | suspected | B |

MERGED: <which into which, or none>
SKEPTICS: <ID → CONFIRMED | PLAUSIBLE | REFUTED, or none run>
RECLASSIFIED: <ID: old → new class and why, or none>
```

Statuses: **confirmed** (measured or a profile share above 5%), **suspected** (not measured), **dropped** (with the reason).

**`6-plan.md`**, which is also what the user sees:

```
# Perf plan — <target>

Baseline: <median> ms (spread <x>%) · peak <n> MB · <n> queries · at <sizes> · <n> runs
Keep rule: a fix stays if its median beats the before by more than <x>%, the output matches and tests pass.
Fixes go to: <where> · Tests: <pass>/<fail> baseline

## Where the time goes
<the top costs from the profile, or the measured findings in scan mode, with their shares>

## Fixes, in order
| # | Finding | Fix | Class | Expected (upper bound) | Measured by |
|---|---|---|---|---|---|
| 1 | PERF-1 | prefetch order lines | P | ≤ 41% | benchmark + query count |
| 2 | PERF-3 | cache tax table per request | B | ≤ 12% | benchmark |

## Needs your decision (B)
<each B fix: what observable behavior changes (stale for how long, which order, which API), who is affected, the skeptic's verdict>

## Recommendations (N)
<each: the decision it needs and the evidence>

## Suspected, not measured
<each with the size where it would matter>

DECISION: <filled in after the user answers>
```

Order the fixes by expected gain, largest first: the profile share caps what a fix can save. Where two fixes touch the same code, put them in the order that keeps each one's measurement meaningful.

**`7-ledger.md`**

```
| # | Finding | Class | Before (median · spread) | After | Gain | Threshold | Memory | Queries | Output | Tests | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PERF-1 | P | 820 ms · 3.1% | 310 ms · 2.8% | 62% | 6.2% | 140 → 142 MB | 202 → 3 | same | 118 pass | kept |
| 2 | PERF-5 | P | 310 ms · 2.8% | 301 ms · 3.5% | 2.9% | 5.6% | = | = | same | 118 pass | discarded: no gain |
| 3 | PERF-3 | B | — | — | — | — | — | — | — | — | declined by user |

PROFILE AFTER KEPT FIXES: <top frames now, or "not re-profiled: <why>">
FILES TOUCHED: <path → fix numbers>
FULL SUITE: <command> · <pass>/<fail> · new failures vs. baseline: <none | list>
FINAL: <median> ms (spread <x>%) vs. baseline <median> ms · <how compared: ab re-run | against Step 3 numbers, load <n> then and <n> now>
SELF-CHECK: <leftover timers, counters, prints or commented-out code found in the diff and removed, or nothing>
```

Verdicts: **kept**, **discarded: no gain / worse / memory tradeoff declined**, **reverted: tests failed / output changed**, **declined** (the user said no), **deferred** (with why), **skipped: no longer hot** (a kept fix took the cost away), **report only**. Every planned fix has exactly one row.

**`report.md`**

```
# Perf report — <target>

<two or three sentences: what was slow, how much faster it is now, at what size, and whether behavior changed>

## Before and after
| Metric | Baseline | Final | Change |
|---|---|---|---|
| Median wall time | | | |
| Spread | | | |
| Peak memory | | | |
| Queries / calls | | | |
Measured: <command> · <sizes> · <runs> runs after <w> warm-up · <machine, load>

## Where the time goes
| Rank | Before | Share | After | Share |
|---|---|---|---|---|

## Fixes kept
<each: what changed, its own before → after, class; for B, what now behaves differently>

## Fixes discarded
<each: what was tried and the numbers that rejected it; often as useful as the kept ones>

## Suspected, not measured
<each: family, where, the size where it would matter>

## Needs your decision
<N recommendations and declined or deferred B fixes: the decision, the evidence, the expected gain>

## Limits
<tools not installed, noise level, what couldn't run, sizes assumed rather than given>

Work files: <work path> (benchmark, profiles, plan, ledger, backups)
```

Lead with the headline number and whether behavior changed. The tables are for reference.
