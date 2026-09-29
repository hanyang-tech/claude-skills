# Review Lenses

Each lens is an independent angle of attack. For each one, start from its **guiding question**, then work through the checklist against the actual code — changed lines *and* the unchanged code they interact with. Checklists are prompts, not exhaustive: skip items that don't apply, and follow anything suspicious even if it isn't listed.

---

## 1. Intent & logic

**Guiding question:** If I only knew the Intent Statement, would I agree this code achieves it — for every case the intent covers?

- Walk through the main scenario from the intent step by step with concrete values. Does the output match?
- Conditions: inverted checks, `&&` vs `||`, wrong operator precedence, negations in the wrong place, `<` vs `<=`, early returns that skip required work.
- Off-by-one: loop bounds, slicing, pagination (`offset`/`limit`, page 0 vs 1), inclusive vs exclusive ranges, fencepost in date ranges.
- Wrong variable: copy-paste slips (`a.x` compared to `a.x` instead of `b.x`), shadowed names, stale variable reused after reassignment, loop variable captured in a closure.
- Types & units: integer division, float equality, rounding of money, signed/unsigned, ms vs s, bytes vs chars, timezone-naive vs aware, string vs number comparison.
- Default values and fallbacks that silently mask a wrong path (`x or default` when `x` can legitimately be `0`/`""`/`False`).
- Does the code do *more* than the intent? Unrelated behavior changes smuggled in, debug code, leftover feature toggles.
- Do the claims in the PR description, comments, and names match what the code does?

## 2. Edge cases & inputs

**Guiding question:** What input or starting state would make this misbehave?

- Empty: empty string, empty list/map, zero rows returned, zero-length file.
- Missing: `null`/`None`/`undefined`, absent keys, optional fields not set, missing env vars or config.
- Boundaries: 0, 1, -1, max int, max length, exactly-at-limit, first/last element, single element.
- Size: very large inputs, deeply nested structures, huge files, long strings.
- Text: Unicode, emoji, combining characters, RTL, case folding, whitespace/newlines, locale-dependent parsing, special characters in names/paths.
- Time: DST transitions, leap years/days, end of month, timezones, clock skew, timestamps in the past/future, epoch 0.
- Duplicates and ordering: duplicate IDs, unsorted input where sorted is assumed, stable-sort assumptions.
- State: first-ever run (no prior data), partially migrated data, records created by an older version, soft-deleted records.
- Types at dynamic boundaries: JSON numbers as strings, booleans as `"false"`, arrays vs single values.

## 3. Failure modes & error handling

**Guiding question:** When something this code depends on fails, what happens — and is it what the author would want?

- Every I/O call (network, DB, file, subprocess, queue): what if it errors, times out, or returns partial data? Is there a timeout at all?
- Swallowed errors: empty `catch`, `except Exception: pass`, ignored return codes, `.catch(() => {})`, unawaited promises/futures whose failures vanish.
- Errors converted to success: returning `[]`/`None`/default on failure so callers can't tell "nothing" from "broken".
- Partial failure: a multi-step operation fails midway — is state left inconsistent? Is there a transaction, rollback, or compensating action?
- Cleanup: files, locks, connections, temp resources released on *every* path, including exceptions (`finally`, `with`, `defer`, `using`).
- Retries: retrying non-idempotent operations, retry without backoff/jitter, unbounded retries, retrying on errors that will never succeed.
- Error messages: leak secrets/PII? Lose the original cause/stack? Are they actionable?
- Exceptions crossing boundaries: does the new code throw a type existing callers don't catch?

## 4. State, concurrency & ordering

**Guiding question:** What happens when this runs twice, concurrently, out of order, or is interrupted?

- Race conditions: check-then-act (`if not exists: create`), read-modify-write without locking or atomic ops, lost updates.
- Shared mutable state: module-level/global/static variables, caches, singletons, mutable default arguments, shared objects across requests or threads.
- Idempotency: can the operation be safely retried or delivered twice (webhooks, queue consumers, form double-submit)?
- Ordering assumptions: events/messages arriving out of order, async callbacks completing in a different order, DB rows without explicit `ORDER BY`.
- Async correctness: missing `await`, blocking calls in async code, fire-and-forget tasks, deadlocks, lock ordering.
- Caching: invalidation on write, stale reads, cache keys missing a dimension (user, tenant, locale), caching errors.
- Lifecycle: initialization order, use-after-close, re-entrancy, component unmount/cleanup in UI code, stale closures in UI hooks.
- Transactions: isolation level assumptions, work done outside the transaction that should be inside (or side effects like emails sent inside a transaction that may roll back).

## 5. Security & trust boundaries

**Guiding question:** Where does untrusted data enter, and can an attacker (or a curious user) make this do something it shouldn't?

- Injection: SQL/NoSQL, shell commands, path traversal, template injection, LDAP, header injection, regex DoS, unsafe deserialization, `eval`.
- XSS / output encoding: unescaped user content in HTML, `dangerouslySetInnerHTML`, `v-html`, markdown rendering, URLs with `javascript:`.
- AuthN/AuthZ: new endpoints or actions missing auth checks; object-level authorization (can user A access user B's resource by changing an ID?); privilege checks on the server, not only in UI.
- Multi-tenancy: queries missing a tenant/owner filter.
- Secrets: credentials, tokens, or keys hard-coded, logged, returned in responses, or committed in config/tests.
- Sensitive data: PII in logs, analytics, error messages, URLs; over-broad API responses exposing internal fields.
- SSRF / open redirect: server fetching user-supplied URLs, redirects to user-supplied locations.
- Crypto & randomness: weak/insecure random for tokens, homemade crypto, non-constant-time comparisons of secrets, disabled TLS verification.
- Resource abuse: missing rate limits or size limits on user-controlled inputs (uploads, pagination size, batch sizes).
- Dependencies: newly added packages — are they reputable, pinned, necessary?

## 6. Contracts, data & compatibility

**Guiding question:** What breaks for code, data, or systems that already exist and weren't part of this diff?

- Changed function/method signatures, return types, raised errors, or nullability — are **all** callers updated (Grep for them)?
- Public API / HTTP / RPC / event schema changes: breaking for existing clients? Versioned? Old mobile app versions still in the wild?
- Serialization: renamed/removed fields, enum values added (do consumers handle unknown values?), date/number format changes.
- Database: migrations reversible? Safe on a large table (locks, full rewrites)? Backfill for existing rows? New `NOT NULL` column without default? Index needed for new queries? Code and migration deployable in either order (old code on new schema and vice versa during rollout)?
- Persisted data written by old code: can the new code read it? Can the old code (during rollback) read data written by the new code?
- Config & feature flags: new config keys have defaults in every environment? Flag default state is safe?
- Semantics preserved: behavior the Intent Statement says must stay the same — does it?

## 7. Performance & resources

**Guiding question:** What happens at 100× the data, traffic, or input size?

- N+1 queries, queries inside loops, missing batching, missing pagination on potentially large result sets.
- Algorithmic complexity: nested loops over large collections, repeated linear searches (`list.includes` in a loop), repeated sorting, quadratic string building.
- Unbounded growth: in-memory caches/maps without eviction, accumulating listeners/subscriptions, loading whole files/tables into memory.
- Work on hot paths: expensive computation, logging, or I/O added to per-request or per-render code; unnecessary re-renders in UI.
- Leaks: unclosed handles, connections not returned to the pool, timers/intervals never cleared.
- Missing indexes for new query patterns; `SELECT *` on wide tables; full-table scans.
- Network: chatty calls that could be batched, missing timeouts, large payloads.

## 8. Tests

**Guiding question:** If this change had a subtle bug, would the tests catch it?

- Is the new/changed behavior tested at all? Is the *risky* part tested, or only the trivial happy path?
- Mentally mutate the code (flip a condition, drop a line, change `<` to `<=`): would any test fail? If not, the test is weak.
- Do tests assert on the outcome, or only that "no exception was thrown"? Snapshot tests that would accept wrong output?
- Are the edge cases and failure modes found under lenses 2–4 covered?
- Over-mocking: are the mocks hiding the exact interaction that could break (e.g., mocking the DB so a wrong query still "passes")?
- Flakiness: dependence on time, randomness, ordering, network, shared state between tests, sleeps.
- Were existing tests changed to make them pass? If an assertion was loosened or a test deleted, is that justified by the intent, or is it hiding a regression?

## 9. Omissions

**Guiding question:** What *should* have changed along with this diff but didn't?

- Sibling code paths: the same logic in another handler, backend, platform, or sync/async twin that still has the old behavior.
- Every place that switches/matches on an enum or type that gained a new variant.
- Callers, docs, API specs, OpenAPI/GraphQL schemas, type definitions, client SDKs.
- Migrations or backfills for a model change; data cleanup for a removed feature.
- Config in every environment (dev/staging/prod), deployment manifests, CI.
- Observability: logs/metrics/alerts for a new failure mode; feature flag cleanup.
- Changelog, user-facing docs, or UI copy when behavior visibly changes.
- Validation added on the frontend but not the backend (or vice versa).

## 10. Maintainability (only what risks future bugs)

**Guiding question:** Will the next person to touch this code likely introduce a bug because of how it's written?

- Duplicated logic that must be kept in sync (and a nearby existing helper that should have been reused).
- Misleading names or comments that contradict the behavior.
- Hidden coupling: magic values shared across files, implicit ordering requirements, action-at-a-distance side effects.
- Overly complex control flow where a simpler structure would make the bug classes above visible.
- Dead code, leftover debugging, commented-out code, TODOs that hide incomplete work the intent depends on.

Keep this lens short in the report. Pure style preferences that the project's linter/formatter doesn't enforce are not findings.
