# Performance antipatterns

Part 1 is the catalog. Step 4 uses it two ways: in scan mode, one family per pass over the scope; in measure mode, to name the cause of a hot frame the profile already found. Part 2 is how Step 5 confirms or drops a finding of each family. The output contracts for `4-findings.md` and `5-verification.md` are in [measuring.md](measuring.md), Part 4.

## Contents

- Fix classes
- Part 1 — The families: N1, QLOOP, INDEX, UNBOUND, MEM, LOOP, QUAD, STR, BLOCK, SEQ, BATCH, POOL, CACHE, LOG, COPY, BUNDLE, RENDER, RETRY, DEFER
- Part 2 — Confirming findings

## Fix classes

| Class | Meaning | Applied |
|---|---|---|
| **P — preserving** | Same results, same order, same errors, same side effects, same API. Only the cost changes: eager loading, a set instead of a list for membership, a regex compiled once, a reused client, a join instead of `+=`. | With plan approval, or with `--auto`, and only if it measured faster |
| **B — behavior-changing** | Something a caller, user, operator or downstream system could observe: caching (stale reads), concurrency (ordering, load on downstream, rate limits), indexes and migrations, pagination (an API change), deferring work (consistency), batching that changes partial-failure behavior, retry timing, removing log lines. | Only with the user's yes to that item, and only if it measured faster |
| **N — needs a decision** | A change the code can't settle: a caching layer, a schema redesign, denormalization, a queue, more workers, a different library. | Never; it goes in the report as a recommendation |

When unsure between two classes, take the stricter one. A P fix whose proof rests on "nothing else mutates this" or "the order doesn't matter" is P only once that is checked against every caller.

**Matters at.** Every finding states the input size where it starts to cost, in the target's own units: rows, items, bytes, requests per second, components on the page. Work it out from the cost per unit and the sizes in `2-setup.md`: 100 extra round trips at about 1 ms each is 100 ms per request. Below that size the finding is real but not worth a change, and the plan says so.

---

## Part 1 — The families

Search with ripgrep over the scope and read every hit in context. A signal is where to look, not a finding. Before recording, check **Not a problem when**.

### N1 — N+1 queries
- **Looks like:** one query per item, through an ORM relation read inside a loop, a serializer or a template, or a GraphQL resolver that loads a relation per parent.
- **Signals:** relation access in loops and serializers (`order.customer.`, `item.product.`); `rg -n 'select_related|prefetch_related|joinedload|selectinload|subqueryload|\.includes\(|\.preload\(|eager_load|include:|with\(|Preload\(|JOIN FETCH|@EntityGraph'` to see where the codebase does eager-load and where it doesn't; GraphQL resolvers calling `findOne`, `get`, `findUnique` per parent without a DataLoader.
- **Matters at:** tens of parents per request on a networked database.
- **Fix:** eager-load (`select_related` / `prefetch_related`, `joinedload` / `selectinload`, `includes` / `preload`, Prisma `include`, GORM `Preload`, `JOIN FETCH`), or a DataLoader per request. P. B if it changes what is serialized or the row order.
- **Not a problem when:** the loop is bounded by a small constant, or the relation is already cached in the identity map.

### QLOOP — Queries and HTTP calls inside loops
- **Looks like:** an explicit `.get()`, `SELECT`, `fetch`, `requests.get`, `http.Get` or RPC per iteration, including `exists()` and `count()` checks.
- **Signals:** `rg -n -B3 '\.(get|filter|find|findOne|findUnique|first|exists|count|query|execute)\(|fetch\(|requests\.|httpx\.|axios\.|http\.(Get|Post)'` and check whether the hit sits in a `for`, `while`, `.map`, `.forEach` or a function called from one.
- **Matters at:** tens of iterations for remote calls; hundreds for a local database.
- **Fix:** one query with `IN (…)` or a join, a bulk endpoint, `bulk_create` / `insert_many` / `createMany`. P for reads. B for writes (transaction and partial failure change) and for third-party calls.

### INDEX — Missing indexes
- **Looks like:** a column used in `WHERE`, `JOIN`, `ORDER BY` or a foreign key lookup with no index, on a table that grows.
- **Signals:** filter and sort fields in queries (`filter(status=`, `.where(`, `order_by(`), compared with the schema: migrations, `schema.prisma` `@@index`, `models.Index` / `db_index=True`, `add_index`, `CREATE INDEX`, `@Index`. Postgres doesn't index foreign keys on its own.
- **Matters at:** thousands of rows; earlier for sorts with `LIMIT`.
- **Fix:** add the index in a migration, in the project's migration tool. Always B: it's a schema change, it locks or slows writes while building (use `CONCURRENTLY` where the project does), and it costs every write.
- **Confirm the plan** with `EXPLAIN` on the scratch database at a realistic row count: a sequential scan before, an index scan after.

### UNBOUND — Unbounded queries and missing pagination
- **Looks like:** `.all()`, `findMany()` with no `take`, `SELECT` with no `LIMIT` behind a list endpoint, an export that grows with the table.
- **Signals:** `rg -n '\.all\(\)|findMany\(\s*\)|findAll\('` and `rg -n -P 'SELECT (?!.*LIMIT).* FROM'` behind handlers; list endpoints without `page`, `cursor`, `limit` parameters.
- **Matters at:** whatever the largest tenant or table holds, not the test fixture.
- **Fix:** pagination (B, an API change), a hard cap (B), streaming or chunked iteration (`iterator()`, `yield_per`, `find_each`, cursors) for internal jobs (P when the consumer reads sequentially).

### MEM — Loading everything into memory
- **Looks like:** reading a whole file, response or table to process it row by row: `read()`, `readFileSync`, `json.load` of a large file, `list(queryset)`, `pd.read_csv` with no `chunksize`, `ioutil.ReadAll`, `.collect()` on a large iterator.
- **Signals:** `rg -n '\.read\(\)|readFileSync|readFile\(|json\.load\(|ReadAll|list\(.*objects|\.to_list\(\)|\.collect::<Vec|read_csv\('`
- **Matters at:** inputs that approach a meaningful share of the process's memory, or many concurrent requests each holding a copy.
- **Fix:** stream or chunk (P when output is identical). Measure peak memory, not only time.

### LOOP — Repeated expensive work in loops
- **Looks like:** work that doesn't depend on the loop variable done on every iteration: compiling a regex, parsing config or JSON, building a formatter, opening a file, creating a client, a lookup that could be a dict built once.
- **Signals:** `rg -n 're\.compile|new RegExp|regexp\.MustCompile|Regex::new|json\.loads|JSON\.parse|yaml\.|strptime|datetime\.strptime|Intl\.|new Date\(|open\('` inside loop bodies and hot functions.
- **Matters at:** thousands of iterations, or any count in a per-request path.
- **Fix:** hoist it out of the loop, or to module level (P). Python caches recent regexes, so check the profile before calling a `re.match` in a loop a finding.

### QUAD — Quadratic work
- **Looks like:** `x in list` inside a loop, nested loops matching two collections, `list.index`, `array.includes` / `indexOf` / `find` in a loop, removing from the front of a list, repeated sorting inside a loop.
- **Signals:** `rg -n ' in [a-z_]+(_list|s)\b|\.includes\(|\.indexOf\(|\.find\(|\.index\(|\.remove\(|\.pop\(0\)|\.shift\(\)|sorted\(|\.sort\('` inside loops.
- **Matters at:** about a thousand items on each side.
- **Fix:** a set or dict built once, a single pass, `deque`, sort once (P, if order and duplicates are kept the same).

### STR — String building in loops
- **Looks like:** `s += …` in a loop in languages where that copies (Java, Go, C#, older Python paths), building HTML or CSV by concatenation.
- **Signals:** `rg -n '\+= *["\x27f]|\+= *str|\+= *String'` in loops.
- **Matters at:** thousands of pieces, or large pieces.
- **Fix:** `"".join`, `StringBuilder`, `strings.Builder`, an array then `join` (P). CPython often optimizes `+=` on a local string, so measure first.

### BLOCK — Blocking I/O in async code
- **Looks like:** synchronous file, network, database or CPU-heavy work inside `async def`, an event-loop callback or a Node request handler: `requests.` in `async def`, `time.sleep`, `fs.*Sync`, `bcrypt.hashSync`, a sync ORM call in an async view, a big `JSON.parse` on the loop.
- **Signals:** `rg -n 'async def' -A40 | rg 'requests\.|time\.sleep|open\(|psycopg2|\.objects\.'`; `rg -n 'Sync\('` in server code.
- **Matters at:** any concurrency above one: every request waits behind the blocked one.
- **Fix:** the async client the codebase already uses, `asyncio.to_thread` / `run_in_executor`, a worker thread, or the non-`Sync` API. P when results and ordering per request are unchanged; B when it moves work to another thread with shared state.
- **Confirm:** measure latency under a few concurrent requests locally, not a single one.

### SEQ — Sequential awaits that could run concurrently
- **Looks like:** independent `await a(); await b(); await c()`, or `for x in xs: await f(x)` where the calls don't depend on each other.
- **Signals:** consecutive `await` lines whose results don't feed each other; `await` inside `for`.
- **Matters at:** two or more calls of noticeable latency on the same path.
- **Fix:** `asyncio.gather` / `TaskGroup`, `Promise.all`, `errgroup`, `tokio::join!`, with a bounded concurrency limit for loops. Always B: ordering of side effects, error behavior (first failure vs. all), and the load on the downstream service change. Check its rate limits.

### BATCH — Chatty calls that could be batched
- **Looks like:** many small calls to the same service where it has a bulk API: per-item cache gets (`get` instead of `mget`), per-row inserts, per-message publishes, per-key S3 or Redis operations.
- **Signals:** single-item client calls in loops; the client library's bulk methods unused (`mget`, `pipeline`, `bulk_create`, `insertMany`, `executemany`, `send_batch`).
- **Matters at:** tens of calls per operation over a network.
- **Fix:** the bulk API. P for reads with identical results. B for writes, since partial failure and transaction behavior change.

### POOL — No connection pooling or client reuse
- **Looks like:** a new HTTP client, session, database connection or SDK client per call or per request: `requests.get` in a hot loop instead of a `Session`, `new PrismaClient()` per request, `httpx.Client()` inside a function, `sql.Open` per call, `new HttpClient()` per request in .NET.
- **Signals:** `rg -n 'requests\.(get|post)|httpx\.(Client|AsyncClient)\(|new PrismaClient|sql\.Open\(|create_engine\(|new HttpClient\(|boto3\.client\('` outside module or startup scope.
- **Matters at:** a few calls per second, sooner over TLS.
- **Fix:** one client per process, created at startup, in the codebase's usual place (P when the client holds no per-call state such as cookies or auth; otherwise B).

### CACHE — Caching opportunities
- **Looks like:** a pure, expensive computation or a slow read called repeatedly with the same inputs: config parsed per request, a permission tree rebuilt per call, the same remote lookup per item.
- **Signals:** the profile showing the same function with the same arguments many times; hot functions with no side effects and stable inputs.
- **Matters at:** repeat rates the call frequency in `2-setup.md` supports.
- **Fix:** memoize within the request or the run (`functools.cache` on a pure function, a dict in scope): P only if the function is pure and the cache can't outlive its inputs. A cache that outlives the request (process-wide, Redis): B, with the staleness window stated. A new caching layer: N.

### LOG — Expensive logging in hot paths
- **Looks like:** formatting or serializing large objects for a log line below the active level (`logger.debug(f"{big}")`, `JSON.stringify` in a debug call), a log line per item in a large loop, synchronous log handlers on the request path.
- **Signals:** `rg -n 'log(ger)?\.(debug|info|trace)\(f"|log.*JSON\.stringify|log.*json\.dumps'` in hot functions.
- **Matters at:** thousands of lines per operation, or large serialized objects.
- **Fix:** lazy formatting (`logger.debug("%s", x)`), `isEnabledFor` guards, the level check the library has (P). Removing or downgrading a log line: B, since operators read it.

### COPY — Unnecessary copies
- **Looks like:** `deepcopy`, `structuredClone`, `JSON.parse(JSON.stringify(x))`, `.clone()` on large values, `list(x)` / `[...x]` / `dict(x)` of data that isn't mutated afterwards, pass-by-value of large structs in Go or C++.
- **Signals:** `rg -n 'deepcopy|structuredClone|JSON\.parse\(JSON\.stringify|\.clone\(\)|copy\.copy'`
- **Matters at:** large objects or copies per item.
- **Fix:** remove the copy (P only after checking every path that holds the value never mutates it; otherwise B), or copy only the part that changes.

### BUNDLE — Large imports and bundles on the web
- **Looks like:** importing a whole library for one function (`import _ from 'lodash'`, `import * as`), heavy libraries in the initial bundle (charting, editors, date libraries with all locales), routes not lazy-loaded, images not sized or lazy.
- **Signals:** `rg -n "import \w+ from '(lodash|moment|date-fns|rxjs|@mui/icons-material|chart\.js)'|import \* as"`; the build's size output (`next build`, `vite build`, `webpack --json`, `source-map-explorer`, `rollup-plugin-visualizer` if installed).
- **Matters at:** initial JavaScript above roughly 200 KB compressed on mobile, or any single dependency that dominates the bundle report.
- **Fix:** named or path imports (P), lighter equivalents the codebase already uses (P or B), `React.lazy` / dynamic `import()` for routes and heavy widgets (B: a loading state appears).

### RENDER — Unneeded React re-renders
- **Looks like:** new object, array or function props created every render and passed to memoized children; context values rebuilt every render; state held too high so a keystroke re-renders the page; `key={index}` on reordered lists; expensive computation in render without `useMemo` where the codebase uses it.
- **Signals:** `rg -n 'value=\{\{|style=\{\{|onClick=\{\(\) =>|key=\{(i|index|idx)\}'`; `React.memo`, `useMemo`, `useCallback` usage elsewhere in the codebase as the baseline.
- **Matters at:** lists of hundreds of rows, or components that render on every keystroke or animation frame.
- **Fix:** stable references, moving state down, `memo` where the codebase uses it (P when props are treated as immutable). Confirm with the React Profiler's commit counts or render timings.

### RETRY — Retries without backoff
- **Looks like:** a retry loop with no delay, a fixed delay, no cap, or no jitter; retries on errors that won't succeed (400s); retries at several layers multiplying.
- **Signals:** `rg -n 'retry|retries|attempt|backoff|for .* in range\(\d+\).*:\s*$'` near network calls.
- **Matters at:** any outage of the downstream service: retries without backoff turn a slowdown into a storm.
- **Fix:** exponential backoff with jitter and a cap, using the retry helper the codebase already has. B, since timing and load change. Measure only against a local stub, never the real service.

### DEFER — Synchronous work in the request path that could be deferred
- **Looks like:** sending email, generating thumbnails or reports, calling webhooks, writing analytics, or updating search indexes inside the request before responding.
- **Signals:** calls to mailers, `requests.post` to webhooks, image libraries, report builders inside handlers; the codebase's task queue (Celery, RQ, Sidekiq, BullMQ, Hangfire) used elsewhere.
- **Matters at:** when that work is a large share of the request's time in the profile.
- **Fix:** enqueue it on the codebase's existing queue. B: the work now happens later, can fail separately, and the response no longer reflects it. No existing queue: N.

---

## Part 2 — Confirming findings

A finding is **suspected** until something measured it. Step 5 confirms each with the check for its family, at the sizes in `2-setup.md`, and drops what doesn't hold.

| Family | Confirm it by | Drop it when |
|---|---|---|
| N1, QLOOP | Counting queries or calls at two sizes, n and 10n, in a test or script against the scratch database or a stubbed client. Linear growth confirms it. | The count is constant, or the loop is bounded small. |
| INDEX | `EXPLAIN` (Postgres `EXPLAIN (ANALYZE, BUFFERS)`, MySQL `EXPLAIN ANALYZE`, SQLite `EXPLAIN QUERY PLAN`) on the scratch database seeded to a realistic row count. | The plan already uses an index, or the table stays small. |
| UNBOUND, MEM | Peak memory and time at the realistic size, and at 10× if it could get there. | The size is bounded by design (an enum table, a config file). |
| LOOP, QUAD, STR, COPY | A micro-benchmark of the function at the realistic size, or the profile share of the line. | Under 5% of the target's time, or the language already optimizes it. |
| BLOCK | Latency of a few concurrent requests against the local server, before and after. A single request won't show it. | The call is fast and bounded (a small local file read at startup). |
| SEQ, BATCH | Number of round trips and the wall time against a local stub with realistic latency injected. | The calls depend on each other, or the downstream forbids parallel or bulk use. |
| POOL | Time and connection count over a loop of calls against a local server. | The client is already reused through a module or a container. |
| CACHE | The profile showing repeated calls with the same arguments, and a hit-rate estimate from the call pattern. | Inputs rarely repeat, or the function isn't pure. |
| LOG | Profile share of logging and formatting at the configured production level. | The line is below the active level and formatted lazily already. |
| BUNDLE | The build's size report before and after; Lighthouse or the Performance panel against the local build if installed. | The module is already code-split or tree-shaken. |
| RENDER | React Profiler commit counts or render durations for the interaction. | The component is cheap and renders rarely. |
| RETRY | Reading the retry code and simulating failure against a local stub; count attempts and timing. | Backoff and caps exist in a lower layer. |
| DEFER | The profile share of the deferrable work in the request. | The response depends on its result. |

In measure mode, a finding also needs a share of the profile: a fix can save at most the share of time its code takes. A finding under about 5% of the target's time goes in the report as minor, not in the plan, unless the user asks.
