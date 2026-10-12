# TypeScript and JavaScript

This is the lowest-ranked standard. The user's patterns, the project's rules and config, and the code around the change all override it. Use it where they are silent.

## Tooling

Use what the project already has, through its own package manager and the scripts in `package.json`. The lockfile says which manager: `package-lock.json` is npm, `pnpm-lock.yaml` is pnpm, `yarn.lock` is yarn, `bun.lock` is bun. The right-hand column is what to look for, and what to propose as a backlog item if a job has no tool.

| Job | Common tools |
|---|---|
| Format | `prettier`, `biome format` |
| Lint | `eslint` with `typescript-eslint`, `biome lint` |
| Types | `tsc --noEmit` |
| Tests | `vitest`, `jest`, `node --test`, `playwright` for end-to-end |
| Coverage | `vitest --coverage`, `jest --coverage` |
| Dependency audit | `npm audit`, `pnpm audit`, `yarn npm audit` |
| Static security | eslint security plugins, `semgrep` |

Read `tsconfig.json` before writing: `strict`, `noUncheckedIndexedAccess`, the module system (ESM or CommonJS) and the target. Never loosen it to make code compile.

## Idioms and structure

- No `any`. Data from outside is `unknown` until narrowed.
- No `as` cast or `!` assertion to quiet the compiler, unless the reason it is safe is visible right there. `@ts-expect-error` with a reason if a suppression is unavoidable, never `@ts-ignore`.
- Validate external data at runtime (API responses, `JSON.parse`, environment variables, form input) with the project's schema library (`zod`, `valibot`). A type annotation checks nothing at runtime.
- Model states as a discriminated union with an exhaustive `switch` (a `never` check in `default`), not a bag of optional fields and booleans.
- `const` by default. `readonly` and `as const` for data that shouldn't change. Don't mutate parameters.
- `===`. `??` for defaults where `0`, `""` or `false` are valid values; `||` only when every falsy value should be replaced.
- `async`/`await`. Every promise is awaited, returned, or handled on purpose.
- Throw `Error` subclasses, not strings. `catch (err: unknown)` and narrow before using it.
- `Map` and `Set` for collections keyed by arbitrary or user-supplied values, not plain objects.
- `import type` for type-only imports. Follow the project on named against default exports.
- React, where it applies: complete dependency arrays, cleanup in every effect that subscribes or schedules, stable keys (not the index for lists that reorder), and derived values computed in render instead of synced with an effect.

## Common bug sources

- A floating promise: its error is lost and its timing is a race. `array.forEach(async ...)` waits for nothing.
- `await` inside a loop where the calls were meant to run together, or `Promise.all` where order or a concurrency limit mattered.
- `||` replacing a valid `0` or `""`, and truthiness tests on numbers and strings.
- `==` coercion, `typeof null === "object"`, `NaN !== NaN`, `Number("")` being `0`, `parseInt("12px")` being `12`.
- `sort()` with no comparator sorts as strings (`[10, 9, 1]` becomes `[1, 10, 9]`). `sort`, `reverse` and `splice` change the array in place.
- An out-of-range index typed as `T` when it is `undefined` (without `noUncheckedIndexedAccess`).
- `this` lost when a method is passed as a callback.
- Dates: `new Date("2024-01-05")` is UTC but `new Date(2024, 0, 5)` is local; months start at 0; an unparseable string gives `Invalid Date` instead of throwing.
- Integers above `Number.MAX_SAFE_INTEGER`, such as large IDs from JSON, and float arithmetic on money.
- Object spread is shallow, so nested state is still shared.
- A stale closure in a hook, timer or event handler reading old state.
- Listeners, intervals and subscriptions that are never removed; a request that is never aborted and resolves after its result is no longer wanted.
- ESM and CommonJS mixed: a default import of a CommonJS module, `__dirname` in ESM.

## Security pitfalls

- Script injection through `innerHTML`, `dangerouslySetInnerHTML`, `v-html` or `document.write` with input that wasn't sanitized, and `javascript:` URLs in `href`.
- SQL built by string concatenation or an untagged template literal. Use parameters or the query builder.
- `child_process.exec` with input (use `execFile` or `spawn` with an argument array). `eval`, `new Function`, and `require` or `import()` of a path built from input.
- Prototype pollution: deep-merging an untrusted object, or `obj[userKey] = value` where the key can be `__proto__` or `constructor`.
- `path.join(base, userInput)` without resolving and checking the result is still under `base`.
- `fetch(userSuppliedUrl)` on the server (request forgery), and redirects to a URL taken from input.
- Secrets in the client bundle: anything prefixed `NEXT_PUBLIC_` or `VITE_` is public. Secrets in logs. Session tokens in `localStorage`.
- `Math.random()` for tokens (use `crypto.randomUUID` or `randomBytes`). `===` to compare secrets (use `crypto.timingSafeEqual`).
- JWTs decoded without verifying the signature, the algorithm, and the expiry.
- A regular expression that backtracks badly, run on user input.
- CORS `*` together with credentials. Cookies missing `HttpOnly`, `Secure` or `SameSite`. No CSRF protection on cookie-authenticated writes.
- Authorization done only in the UI. Every API route and server action checks the caller itself.
- `fetch` with no timeout (`AbortSignal.timeout`).

## Testing conventions

- The project's runner and layout (`*.test.ts` beside the code, or `__tests__/`). Test names state the behavior.
- Await or return every async assertion: `await expect(promise).rejects.toThrow(...)`. An assertion that isn't awaited passes without running.
- Fake timers instead of real waits. Restore mocks between tests.
- Mock at the boundary: the network with `msw` or an injected client, not internal modules.
- UI: Testing Library queries by role and label, `userEvent` for interaction, and assertions about what the user sees. A snapshot is not enough on its own.
- Don't cast to `any` to call code with bad input. Send the bad input through the runtime validation path, which is what will meet it in production.
- `test.each` for boundaries.

## Edge cases to always try

- `undefined`, `null` and a missing key, which are three different things. `""`, `0`, `false`, `NaN`.
- An empty array or object, one element, duplicates.
- Negative numbers, `-0`, non-integers, values past `Number.MAX_SAFE_INTEGER`, numeric strings.
- Emoji and other characters outside the basic plane (`"👍".length` is 2), whitespace, very long strings.
- Dates across a timezone boundary and a daylight-saving change, and `Invalid Date`.
- JSON with extra fields, wrong types, or a `__proto__` key.
- A promise that rejects, one that never settles, and responses arriving out of order (the older request finishing last).
- The same action twice in quick succession (double submit), and after the component unmounted or the request was aborted.
- For UI in scope: offline, a slow network, back and forward navigation, and a refresh mid-flow.
