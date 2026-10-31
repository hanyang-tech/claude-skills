# Failure catalog

Part 1 is how to find failure points (Step 3). Part 2 is the catalog of failures, used to fill the inventory and the matrix (Steps 3 and 4). Part 3 rates gaps and verifies them (Steps 4 and 5). Part 4 is how to simulate each failure in a test (Steps 7 and 8). The file shapes are in `formats.md`.

## Contents

- Part 1 — Failure points: the kinds and how to find them
- Part 2 — The failures: TIME, CONN, 5XX, 4XX, SHAPE, PART, DUP, RACE, CRASH, ORDER, FS, HOSTILE, EDGE, CLOCK, EXHAUST, SLOW, CANCEL, WRONG
- Part 3 — Impact, severity and verification
- Part 4 — Simulating failures, per ecosystem

---

## Part 1 — Failure points

A failure point is any place where the operation depends on something it doesn't control: another process, the disk, the clock, another request, or the input. Trace the call graph from the entry point and stop at each one.

Search with ripgrep over the files the call graph reaches, and read every hit in context. In the table, `\|` is the regex `|`, escaped for the table. A hit is where to look, not a failure point, and a failure point is often hidden in a helper, a base class or a decorator the search doesn't match.

| Kind | What it is | Signals | Failures that usually apply |
|---|---|---|---|
| `http` | HTTP, gRPC or GraphQL calls to another service | `requests\.\|httpx\|aiohttp\|urlopen\|fetch\(\|axios\|got\(\|http\.(Get\|Post\|NewRequest)\|\.Do\(\|reqwest\|HttpClient\|RestTemplate\|WebClient\|OkHttp\|Net::HTTP\|Faraday\|grpc` | TIME, CONN, 5XX, 4XX, SHAPE, SLOW, WRONG, DUP (on retry), CANCEL |
| `sdk` | A third-party client library: cloud, payments, email, LLM | `boto3\|@aws-sdk\|google\.cloud\|stripe\|twilio\|sendgrid\|openai\|anthropic\|aws-sdk-go` | as `http`, plus the SDK's own retries and exceptions |
| `db` | Reads, writes, transactions, migrations | `session\.(add\|commit\|execute)\|\.objects\.\|cursor\.execute\|prisma\.\|knex\|typeorm\|\.query\(\|db\.(Exec\|Query)\|sqlx\|diesel\|jdbcTemplate\|@Transactional\|\.save!?\b\|transaction` | TIME, CONN, PART, DUP, RACE, CRASH, EXHAUST, SLOW, 4XX-like constraint errors |
| `queue` | Publishing or consuming messages and events, enqueuing jobs | `publish\|send_message\|enqueue\|apply_async\|\.delay\(\|kafka\|sqs\|pubsub\|amqp\|bullmq\|nats\|@KafkaListener\|perform_async` | DUP, ORDER, PART, CRASH, TIME, SHAPE (consumer), poison messages |
| `fs` | Reading and writing files, temp files, uploads | `open\(\|\.read_text\|\.write_text\|fs\.(read\|write)\|os\.(Open\|Create\|ReadFile\|WriteFile)\|std::fs\|Files\.\|File\.(open\|read\|write)` | FS, CRASH (half-written file), EDGE (huge, empty), EXHAUST (handles), HOSTILE (paths) |
| `proc` | Subprocesses and shell commands | `subprocess\|os\.system\|child_process\|execFile\|spawn\(\|exec\.Command\|Command::new\|ProcessBuilder\|Open3\|system\(` | TIME, non-zero exit, SHAPE (output), HOSTILE (injection), CANCEL, EXHAUST |
| `parse` | Deserializing and converting: JSON, YAML, CSV, numbers, dates, enums | `json\.loads\|JSON\.parse\|json\.Unmarshal\|serde_json\|ObjectMapper\|yaml\.\|csv\.\|int\(\|parseInt\|Decimal\(\|strptime\|fromisoformat\|Date\.parse\|model_validate\|\.parse\(` | SHAPE, HOSTILE, EDGE, CLOCK (date strings) |
| `auth` | Authentication and permission checks, token handling | `login_required\|permission\|authorize\|@PreAuthorize\|can\?\|jwt\.\|verify\|session\[` | 4XX (401, 403), CLOCK (expiry), HOSTILE, CACHE staleness |
| `clock` | Reading the time, scheduling, expiry, durations | `now\(\|utcnow\|time\.time\|Date\.now\|new Date\(\|time\.Now\|Instant\.now\|LocalDateTime\|Time\.now\|today\(` | CLOCK, ORDER, EDGE (month ends, leap days) |
| `cache` | In-process and remote caches | `cache\|redis\|memcache\|lru_cache\|get_or_set` | CONN, TIME, WRONG (stale), RACE (stampede), EXHAUST |
| `lock` | Mutexes, distributed locks, row locks | `Lock\(\|Mutex\|synchronized\|FOR UPDATE\|advisory\|redlock\|flock` | TIME (acquire), CRASH (lock never released), RACE, EXHAUST |
| `input` | Anything the caller controls: body, query, headers, CLI args, env vars, uploaded files, message payloads | request models, argument parsers, `request\.`, `req\.body`, `os\.environ`, `process\.env`, `ARGV` | HOSTILE, EDGE, SHAPE |

A sequence of two or more writes to different systems (database then queue, charge then insert, file then database) is itself a failure point for PART and CRASH. Give it its own `FP`, located at the function that runs the sequence.

---

## Part 2 — The failures

Each entry says where it **applies**, what **good handling** usually looks like, the **gaps** to look for, and how to **simulate** it. Good handling is the usual answer, not the expected behavior: the expected behavior comes from the sources in Step 2, and this is what to recommend when they are silent.

### TIME — Timeout
- **Applies:** every `http`, `sdk`, `db`, `queue`, `proc` and `lock` call.
- **Good handling:** an explicit timeout on every call, shorter than the caller's own deadline. A timeout surfaces as its own error (504 to an HTTP caller, a retryable error to a job runner). Retries only for idempotent calls, bounded, with backoff and jitter. A warning log naming the dependency, the elapsed time and the request's identifiers.
- **Gaps:** no timeout, so the library default applies (often none, see Part 3). A timeout longer than the caller's, so the caller gives up while the work goes on. A timeout caught as a generic error and reported as a 500 or "not found". A non-idempotent write retried after a timeout, when the first attempt may have succeeded.
- **Simulate:** the HTTP fake delays longer than the configured timeout, or raises the client's timeout exception. Set the timeout low in the test rather than waiting. Go: `httptest.Server` handler that blocks on a channel, with a short `context.WithTimeout`.

### CONN — Connection refused, DNS, TLS
- **Applies:** `http`, `sdk`, `db`, `cache`, `queue`.
- **Good handling:** treated as transient: retried with backoff where the call is idempotent, or failed fast with a clear error. A circuit breaker if the codebase has one. The user sees "service unavailable", never a hostname or a stack trace.
- **Gaps:** the exception escapes as an unhandled 500 with internals. A cache outage takes the whole request down when the cache was optional. Retries without backoff.
- **Simulate:** point the client at a closed port (`127.0.0.1:1`), or have the fake raise the client's connection error (`httpx.ConnectError`, `requests.ConnectionError`, `ECONNREFUSED`, `*net.OpError`).

### 5XX — Server error from a dependency
- **Applies:** `http`, `sdk`.
- **Good handling:** 500, 502, 503 and 504 retried for idempotent calls with a bounded budget, then mapped to 502 or 503 for the caller. `Retry-After` honored on 503. The response body is not parsed as if it were a success.
- **Gaps:** status not checked, so the error body is parsed as data. Every 5XX retried immediately and without limit. A 500 from the dependency passed through to the user with its body.
- **Simulate:** the fake returns 500 or 503 with an HTML or empty body. For retries, return 503 twice then 200, and assert the attempt count.

### 4XX — Client errors from a dependency
- **Applies:** `http`, `sdk`, `auth`, and constraint violations from `db`.
- **Good handling:**
  - 400 and 422: a bug or bad input, not retried. Surfaced with the dependency's reason, logged as an error.
  - 401: refresh the credential once and retry, then fail. 403: a permission error, surfaced, not retried.
  - 404: decided per call. Either a domain "not found" or a bug, never silently `None`.
  - 409 and unique-constraint violations: a conflict the caller sees, or a re-read and retry when the codebase does that.
  - 429: honor `Retry-After`, back off, and keep a budget. Not counted as an outage.
- **Gaps:** every 4XX handled the same way. 4XX retried. 429 retried at full speed. 401 refresh loops. A 404 turned into an empty result that looks like success.
- **Simulate:** the fake returns each status with the dependency's real error body. For 401 refresh, return 401 then 200, and assert one refresh. For constraints, insert the conflicting row first.

### SHAPE — Malformed or unexpected response
- **Applies:** every `http`, `sdk`, `queue` consumer, `proc` output and `parse` of data from outside.
- **Good handling:** validated at the boundary against a schema or typed model. A missing or wrongly typed field fails with an error that names the field. Unknown extra fields are tolerated. Defaults only where the contract says the field is optional.
- **Gaps:** `KeyError`, `undefined` or a nil dereference deep in the code. A missing field silently defaulted to `0`, `""` or `[]`. Non-JSON (an HTML error page, an empty body) crashes the parser with a generic error. An unknown enum value crashes instead of being rejected or mapped.
- **Simulate:** the fake returns valid JSON missing a required field, a field of the wrong type, `null`, an unknown enum value, an empty body, and HTML with `200`.

### PART — Partial failure mid-sequence
- **Applies:** any operation that writes to more than one place, or writes in several steps: database then queue, charge then record, upload then register, a loop of writes.
- **Good handling:** one of these, by the codebase's precedent:
  - one transaction around writes to one database
  - an outbox, so the database write and the message commit together
  - steps ordered so a failure leaves a state that can be retried, each step idempotent, and the operation resumable
  - a compensating action for steps that can't be rolled back, such as a refund
  - for batches, per-item results, so one bad item doesn't fail or half-apply the rest silently
- **Gaps:** an external call inside a database transaction (the call succeeds, the transaction rolls back). The message published before the commit, or after it with nothing to retry it. A loop that stops at the first failure and reports success for the earlier items or none at all. A status set to `processing` with nothing to move it on.
- **Simulate:** a fault-injecting fake that fails on step N (the second call, the third item). Assert the state after: what is persisted, what was sent, and that a retry of the whole operation reaches a correct end state.

### DUP — Duplicate delivery or retried request
- **Applies:** queue consumers (at-least-once delivery), webhook handlers, any endpoint a client or proxy may retry, jobs that can run twice, and every write that is retried after TIME.
- **Good handling:** an idempotency key stored with the result, a unique constraint the duplicate hits, an upsert, or a processed-messages table. A second delivery returns the first result and changes nothing.
- **Gaps:** a counter incremented, an email sent or a charge made twice. A check-then-insert without a constraint behind it, which two concurrent duplicates both pass.
- **Simulate:** call the operation twice with the same input or message, then twice concurrently. Assert one effect.

### RACE — Concurrent modification, lost update
- **Applies:** read-modify-write on shared state (rows, files, cache entries, in-memory maps), check-then-act, counters and balances, anything two requests or workers can touch at once.
- **Good handling:** an atomic update (`UPDATE … SET n = n - 1 WHERE n > 0`), optimistic locking with a version column, `SELECT … FOR UPDATE`, a unique constraint, or compare-and-set. A conflict surfaces as 409 or a retry, never a silent overwrite.
- **Gaps:** read, change in code, write back. A uniqueness check in code only. Shared mutable state in a module or singleton under a threaded or async server.
- **Simulate:** run two operations at once against the same record with a barrier between their read and their write (a hook in the fake repository, a `threading.Barrier`, a `CountDownLatch`, two goroutines with a channel). Assert the final state. Go: run with `-race`. Against a real database, use two connections.

### CRASH — Crash or restart mid-operation
- **Applies:** jobs, consumers, multi-step operations, file writes, anything holding a lock or a lease.
- **Good handling:** a message acknowledged only after processing. Progress persisted, so a restarted job resumes or restarts safely. Leases and locks that expire. Files written to a temp path and renamed into place. Nothing stuck forever in an `in_progress` state.
- **Gaps:** ack before processing. A lock with no expiry. A status flag set at the start and cleared only on success. A file overwritten in place.
- **Simulate:** raise an exception (or `SystemExit`, or a panic) between two steps, then run the operation again from scratch, as a restart would. Assert the end state is correct and nothing is stuck.

### ORDER — Out-of-order events
- **Applies:** event and webhook consumers, replication, anything applying updates from another system, parallel consumers of one stream.
- **Good handling:** a version, sequence number or source timestamp on each event. Stale events ignored. Or the state re-read from the source of truth instead of applying the event's payload.
- **Gaps:** `updated` applied before `created`. An older status overwriting a newer one. A delete followed by a late update that resurrects the record.
- **Simulate:** deliver the events in reverse or shuffled order, and deliver an old one after a new one. Assert the final state matches the in-order result.

### FS — Disk full, permission denied, missing file
- **Applies:** `fs` points, temp directories, config and certificate files read at runtime.
- **Good handling:** the error surfaces with the path and the operation. Atomic writes (temp file, flush, rename). Temp files cleaned up on failure. A missing config file fails at startup with a clear message, not at the first request.
- **Gaps:** a half-written file left in place. The error swallowed and an empty result returned. Temp files leaking. A missing file reported as "invalid format".
- **Simulate:** a read-only temp directory (`chmod 0o500`, skipped when running as root), a missing path, and a writer that raises `ENOSPC` (Python `OSError(errno.ENOSPC, …)`, Go an `io.Writer` returning `syscall.ENOSPC`, Linux `/dev/full`).

### HOSTILE — Invalid and hostile input
- **Applies:** every `input` point, and every `proc`, `db` and `fs` call that takes part of it.
- **Good handling:** validated at the edge by the codebase's schema library, with a 400 or 422 naming the field. Queries parameterized. Paths resolved and checked to stay inside their root. Sizes and counts bounded. Shell commands built as argument lists. Errors to the user say what was wrong and nothing about the internals.
- **Gaps:** input reaching a query, a path, a shell, a template or a redirect unchecked. A validation error that returns 500 with a stack trace. Mass assignment of fields the user shouldn't set.
- **Simulate:** wrong types, missing fields, extra fields, `../` paths, `'; --`, `$(…)`, very long strings, negative and huge numbers, and IDs belonging to another user. Property-based tests where the project has them (Hypothesis, fast-check, proptest, jqwik).

### EDGE — Empty, huge, unicode and boundary input
- **Applies:** `input`, `parse`, and data from `db`, `http` and `fs` that the code iterates or sizes.
- **Good handling:** empty collections and zero handled as their own case. Huge inputs streamed or paginated, with limits. Text treated as Unicode throughout: normalization where comparing, byte versus character lengths where it matters. Off-by-one boundaries tested at the limit, below it and above it.
- **Gaps:** `max([])`, division by zero, `[0]` on an empty list. A whole file or table loaded into memory. Truncation that splits a multi-byte character. Pagination that drops the last page.
- **Simulate:** `[]`, `""`, `0`, `-1`, the max value, the exact limit and limit ± 1, a 50 MB payload, emoji, combining characters, right-to-left text, a null byte.

### CLOCK — Clock skew, time zones, DST
- **Applies:** `clock` points, expiry and token checks, scheduling, date arithmetic, anything that compares times from two machines or stores local times.
- **Good handling:** UTC with time-zone-aware values inside. A monotonic clock for durations and timeouts. Tolerance for skew in expiry checks. Local time only at the edge, with the user's zone. The clock injected, so tests can control it.
- **Gaps:** naive datetimes mixed with aware ones. Durations measured with wall-clock time. "Tomorrow" computed as now + 24 hours across a DST change. A daily job at 02:30 local that runs twice or never on DST days. Month arithmetic on the 31st.
- **Simulate:** freeze the clock inside a DST transition (the skipped hour in spring, the repeated hour in autumn; look up the dates for the zones the code uses, such as `Europe/London` and `America/New_York`), at the end of a month, on a 29 February, at midnight UTC in a far-off zone, and with the remote clock five minutes ahead.

### EXHAUST — Resource exhaustion
- **Applies:** connection pools, threads and workers, memory, file handles, sockets, queue depth, rate budgets.
- **Good handling:** resources released on every path (`with`, `defer`, `try`/`finally`, `using`). Pool acquisition with a timeout. Bounded queues and concurrency. Large data streamed. A pool-exhausted error surfaced as 503, not a hang.
- **Gaps:** a connection, file or response body not closed on the error path. Unbounded `gather` or `Promise.all` over user-sized input. An unbounded in-memory cache.
- **Simulate:** a pool of size one with a held connection, then call the operation and assert it fails within its timeout. Fail on the error path and assert the resource was released (count open handles, check the fake's `closed` flag, Go `goleak`).

### SLOW — Slow dependency
- **Applies:** any `http`, `sdk`, `db` or `lock` call on a request path. Latency, not failure.
- **Good handling:** no lock, transaction or pooled connection held across a remote call. Slow work moved off the request path. Timeouts and concurrency limits so one slow dependency can't take every worker.
- **Gaps:** an HTTP call inside a database transaction or while holding a lock. Sequential calls that could be concurrent, on a path with a deadline.
- **Simulate:** the fake responds just under the timeout, and the test asserts what else was held during the wait: the transaction open, the lock taken, the pool slot used.

### CANCEL — Cancellation and client disconnect
- **Applies:** async code, request handlers doing long work, streaming responses, anything taking a context or abort signal.
- **Good handling:** cancellation propagated to downstream calls (`context.Context`, `AbortSignal`, `CancellationToken`). Cleanup on cancel. Python's `CancelledError` re-raised, never swallowed by `except Exception` (it is a `BaseException` since 3.8, but `except BaseException` and bare `except` still catch it). No half-committed work.
- **Gaps:** downstream work continuing after the client left. Cancellation swallowed and turned into an error log or a retry. A transaction left open.
- **Simulate:** cancel the task or the context mid-call (`task.cancel()`, `controller.abort()`, `cancel()` on the context) while the fake is waiting, then assert cleanup and that no further calls were made.

### WRONG — Success with wrong data
- **Applies:** `http`, `sdk`, `cache` and `db` reads whose result is trusted: payments, balances, IDs, pagination, anything reconciled later.
- **Good handling:** invariants checked on what comes back: the ID matches the request, the currency and amount match, the page token advances, the count is plausible. Mismatches fail loudly and are logged with both values.
- **Gaps:** a `200` with an empty list treated as "no data" when it means "wrong account". A stale cache served after a write. A paginated loop that stops early or loops forever.
- **Simulate:** the fake returns success with a different ID, another currency, a repeated page token, an empty page then more data, or an old cached value.

---

## Part 3 — Impact, severity and verification

**Impact classes**, for every gap and unknown:

| Code | Impact | Example |
|---|---|---|
| LOSS | Data loss or corruption | a write lost on a race, a file half-written in place |
| STATE | Inconsistent state across systems or records | charged but no order, order but no event, stuck `in_progress` |
| SILENT | Silent failure: no error, no log | an exception swallowed and an empty list returned |
| USER | A wrong or leaky error to the caller | 500 for bad input, a stack trace or hostname in the response |
| AMPLIFY | Retry storm or amplification | retries without backoff, retries at several layers multiplying |
| RESOURCE | Resource leak or exhaustion | a connection not returned on the error path |
| SECURITY | Security exposure | injection, path traversal, an auth check skipped on an error path, secrets in logs |

**Severity:**

| Severity | Meaning |
|---|---|
| 🔴 | LOSS, STATE or SECURITY on a path that realistically happens: a retry, a timeout, a redelivery, two users at once |
| 🟠 | SILENT, AMPLIFY or RESOURCE on a realistic path, or a 🔴 impact on a path that needs an unusual combination |
| 🟡 | USER, or any impact on a narrow path with an easy recovery |

**Verification.** Try to disprove every gap and unknown before it reaches the plan:

| Check | How |
|---|---|
| Reachable | Can this failure happen here in production? An in-process SQLite file doesn't get DNS errors. A value from a validated model isn't hostile at the next layer. A single-worker cron job doesn't race itself, unless it can overlap with its next run. |
| Handled upstream | Read the middleware, the framework's error handlers, decorators on the function and its callers (`@retry`, `@transactional`, tenacity, resilience4j, Polly), database constraints and triggers, the queue's redelivery and dead-letter settings, the load balancer or gateway timeout. A handler that exists but doesn't cover this failure is not handling. |
| The library default | Check the installed version's source or docs, not memory. The common ones, as a starting point only: |

| Library | Default timeout | Default retries |
|---|---|---|
| Python `requests` | none, waits forever | none |
| Python `httpx` | 5 s | none |
| Python `aiohttp` | 5 min total | none |
| `boto3` / botocore | 60 s connect and read | yes, by retry mode |
| Node `fetch` (undici) | no overall timeout; headers and body 300 s each | none |
| `axios` | none (`0`) | none |
| Go `http.DefaultClient` | none | none |
| Java `java.net.http.HttpClient` | none | none |
| OkHttp | 10 s connect, read and write | on connection failure only |
| Ruby `Net::HTTP` | 60 s open and read | idempotent requests once |
| Rust `reqwest` | none | none |
| SQLAlchemy pool, HikariCP | 30 s to acquire a connection | — |

- **Expected behavior has a source.** Re-read the cited source for each gap. If it doesn't say what the row claims, the verdict is `unknown`.
- **Skeptics** (agent mode): every gap with impact LOSS, STATE or SECURITY. The brief is the row's claim, its location and the repository path, nothing else.
- **Merge** rows that are one cause: a missing timeout behind TIME, SLOW and EXHAUST is one gap with one fix, listed under all its rows.

---

## Part 4 — Simulating failures, per ecosystem

Simulate at the boundary: fake the HTTP server, the clock, the repository or the file system, not the function under test. Use what the project already has installed, found in Step 2. If nothing fits, write a small fake that implements the boundary's interface and fails on demand. Never install a library for it without the user's yes.

**Techniques:**
- **Boundary fake:** an HTTP mock library or a local test server, configured per test to return statuses, bodies, delays or connection errors.
- **Fault-injecting wrapper:** wraps the real repository, client or writer and fails on the Nth call, or blocks until released. This is how PART, CRASH, RACE and SLOW are simulated.
- **Controlled clock:** freeze or move time instead of sleeping.
- **Concurrent harness:** two operations started together with a barrier between their read and their write, so the race happens every run, not by luck.
- **Real dependency in a container:** only if the project already uses testcontainers or a compose file for tests. It gives real constraint and locking behavior for DUP and RACE.

| Need | Python | JS/TS | Go | Rust | Java | Ruby |
|---|---|---|---|---|---|---|
| HTTP fake | `respx` (httpx), `responses` (requests), `aioresponses`, `pytest-httpserver` | `msw`, `nock`, undici `MockAgent` | `httptest.NewServer`, a custom `RoundTripper` | `wiremock`, `httpmock`, `mockito` | WireMock, OkHttp `MockWebServer` | WebMock, VCR |
| Raise from a dependency | `unittest.mock.patch(..., side_effect=Exc)`, `monkeypatch` | `vi.spyOn` / `jest.spyOn(...).mockRejectedValue` | an interface fake returning the error | a trait fake | Mockito `thenThrow` | `allow(...).to receive(...).and_raise` |
| Fail on the Nth call | `side_effect=[ok, ok, Exc()]` | `mockResolvedValueOnce` chained, then `mockRejectedValueOnce` | a fake with a call counter | a fake with an `AtomicUsize` | `thenReturn(a).thenThrow(e)` | `and_return(a).and_raise(e)` ordered |
| Clock | `freezegun`, `time-machine` | `vi.useFakeTimers()` + `vi.setSystemTime`, `jest.useFakeTimers`, `@sinonjs/fake-timers` | an injected clock, `testing/synctest` (Go 1.25+) | `tokio::time::pause` + `advance` | `Clock.fixed`, `Clock.offset` | `travel_to` (Rails), Timecop |
| Timeout and delay | `asyncio.sleep` in a fake, `httpx.TimeoutException` | fake timers + a never-resolving promise | a handler blocking on a channel, `context.WithTimeout` | `tokio::time::sleep` in a fake | `MockWebServer` `setBodyDelay`, WireMock `withFixedDelay` | WebMock `to_timeout` |
| Cancellation | `task.cancel()`, `asyncio.wait_for` | `AbortController.abort()` | `cancel()` on the context | drop the future, `CancellationToken` | `Future.cancel(true)`, `Thread.interrupt()` | `Thread#raise`, `Timeout.timeout` |
| Concurrency | `threading.Barrier`, `asyncio.gather`, two DB sessions | `Promise.all` with a deferred gate | goroutines + `sync.WaitGroup`, `go test -race` | `tokio::join!`, `loom` if used | `CountDownLatch`, `ExecutorService` | `Thread.new` + `Queue` gate |
| Files | `tmp_path`, `chmod`, `OSError(errno.ENOSPC, ...)` | `os.tmpdir()` + `fs.mkdtemp`, `memfs` | `t.TempDir()`, `iotest.ErrReader`, a failing `io.Writer` | `tempfile`, a failing `Write` impl | `@TempDir`, Jimfs | `Dir.mktmpdir`, `FakeFS` |
| Generated input | Hypothesis | fast-check | `testing/quick`, native fuzzing (`go test -fuzz`) | `proptest` | jqwik | `rantly`, property tests if present |
| Resource leaks | `ResourceWarning` as error (`-W error::ResourceWarning`) | `--detectOpenHandles` (jest) | `goleak` | drop checks in the fake | assert pool active count | count open connections in the fake |

**Writing the test:**
- Name it for the failure and the expectation: `test_charge_timeout_returns_504_and_writes_no_order`, `it("ignores a stale order.updated event")`.
- Assert the expected behavior from the matrix, all of it: what the caller gets, what is persisted, what is sent, and the log line (with `caplog`, a test logger, or the codebase's log capture helper) where the fix adds one.
- Assert the state after the failure, not only the error. Most PART, DUP, RACE and CRASH gaps are invisible in the return value.
- Keep it deterministic: barriers instead of sleeps, a frozen clock instead of real time, a fixed seed for generated input.
- When a gap test fails, read the failure. It has to fail on the assertion the gap predicts. A test that fails on a fixture or an import proves nothing.
