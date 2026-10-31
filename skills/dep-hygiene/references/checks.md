# Checks

Part 1 is the inventory and baseline (Step 2). Part 2 is the eight checks (Step 3). Part 3 is how each check's findings are verified (Step 4). Part 4 is planning and applying (Steps 5 and 6). The output contract for every work file is in [formats.md](formats.md).

## Contents

- Tools, the network and classes
- Part 1 — Inventory and baseline
- Part 2 — The checks: VULN, UNUSED, MISSING, MISPLACED, OVERLAP, OUTDATED, POLICY, BOUND
- Part 3 — Verifying findings
- Part 4 — Planning and applying

## Tools, the network and classes

**Use what is installed.** Find a tool with `command -v <tool>`, `ls node_modules/.bin/<tool>`, `<python in the project env> -m <tool> --version`, `cargo <subcommand> --version`, or `mvn help:describe` against a plugin already in `~/.m2/repository`. Never fetch a tool to run it: no `npx` without `--no-install`, `pnpm dlx`, `yarn dlx`, `bunx` of an uninstalled package, `uvx`, `pipx run`, `go run …@latest`, `cargo install`, or a Maven or Gradle plugin that isn't already cached or configured in the build. A tool that isn't there means the check's fallback, or a line saying "not run: <tool> not installed".

**The network.** Commands marked 🌐 query a registry or advisory database. Run them only when Step 1 recorded the network as available. Packages from a private registry or scope (`.npmrc` scopes, `--index-url` / `[[tool.uv.index]]` / `[[tool.poetry.source]]`, `GOPRIVATE`, a private gem source, `nuget.config`) are never sent to a public service such as osv.dev, PyPI's JSON API or a public registry page. Exclude them from the input, and list them as "private, not checked" in the inventory.

**Raw output.** Save every tool's output to `<work>/raw/<check>-<manifest slug>.<json|txt>`, and cite it in the finding.

**Classes.** Every finding's fix gets one. When unsure, take the stricter one.

| Class | What | Applied |
|---|---|---|
| **A — routine** | Remove a verified-unused package, move a misplaced one, a patch or minor update, including one that fixes a vulnerability | With plan approval, or with `--auto` |
| **R — with approval** | Declare a missing dependency at its resolved version, dedupe a lockfile, an override or resolution for a transitive vulnerability, a small policy fix | With plan approval |
| **M — major** | A major upgrade, including a vulnerability fix that needs one. In 0.x, a minor bump counts as major. In Go, a new `/vN` path | A yes for each |
| **B — behavior-changing** | Consolidating overlapping libraries, replacing a deprecated package, fixing a boundary violation in code | A yes for each |
| **N — report only** | Abandoned packages, a vulnerability with no fixed version, a boundary violation with no clear fix, a pinning-policy decision | Never; it goes in the report |

**Severity.**

| | Meaning |
|---|---|
| 🔴 | Breaks or exposes now: a critical or high vulnerability that is called or imported at runtime, a malicious-package advisory, a missing runtime dependency, a dev-only package imported by shipped code |
| 🟠 | Costs: other vulnerabilities, unused runtime packages, overlapping libraries, majors behind, deprecated packages, import cycles, layering violations, a lockfile out of sync |
| 🟡 | Noise: unused dev packages, patch and minor updates, duplicate transitive versions, style inconsistencies in version ranges |

---

## Part 1 — Inventory and baseline

**Manifests and managers.** Search with `git ls-files` plus untracked files, skipping `node_modules`, `vendor`, `.venv`, build output and fixtures.

| Ecosystem | Manifests | Lockfile → manager | Workspaces |
|---|---|---|---|
| JS/TS | `package.json` | `package-lock.json` / `npm-shrinkwrap.json` → npm · `pnpm-lock.yaml` → pnpm · `yarn.lock` → yarn (v1 if it starts `# yarn lockfile v1`, berry if it has `__metadata:`) · `bun.lock` / `bun.lockb` → bun. The `packageManager` field names the version | `workspaces` in `package.json`, `pnpm-workspace.yaml` |
| Python | `pyproject.toml` (`[project]` deps, optional-dependencies, `[dependency-groups]`, `[tool.poetry.*dependencies]`, `[tool.pdm]`), `requirements*.txt`, `requirements*.in`, `setup.cfg`, `setup.py`, `Pipfile` | `uv.lock` → uv · `poetry.lock` → poetry · `pdm.lock` → pdm · `Pipfile.lock` → pipenv · `.in` compiled to `.txt` → pip-tools · `requirements.txt` alone → pip, no lock | `[tool.uv.workspace]` |
| Go | `go.mod` | `go.mod` is the lock under minimal version selection; `go.sum` holds checksums | `go.work` |
| Rust | `Cargo.toml` (`dependencies`, `dev-dependencies`, `build-dependencies`, features) | `Cargo.lock` → cargo | `[workspace] members` |
| Ruby | `Gemfile`, `*.gemspec` | `Gemfile.lock` → bundler | — |
| Java/Kotlin | `pom.xml`, `build.gradle(.kts)`, `gradle/libs.versions.toml` | none by default · `gradle.lockfile` when locking is on | Maven `<modules>`, `settings.gradle` |
| .NET | `*.csproj`, `Directory.Packages.props` | `packages.lock.json` when enabled → dotnet | the `.sln` |

Two lockfiles from different managers for one manifest is a POLICY finding. The manager that CI installs with is the one in use. If CI doesn't say, ask. Never switch managers, and never regenerate a lockfile with a different manager.

**Direct dependencies with resolved versions.**

| Manager | Command |
|---|---|
| npm | `npm ls --depth=0 --json` · runtime only `--omit=dev` |
| pnpm | `pnpm ls --depth 0 --json -r` |
| yarn | v1 `yarn list --depth=0 --json` · berry `yarn info --name-only --recursive` |
| uv | `uv tree --depth 1` · `uv export --format requirements-txt --no-hashes` for the full pinned set |
| poetry | `poetry show --top-level` · `poetry show --only main` |
| pip | `<venv python> -m pip list --format json` |
| go | `go list -m -json all` (direct: `Indirect` false) |
| cargo | `cargo tree --depth 1 -e normal,dev,build` |
| bundler | `bundle list` · groups from the `Gemfile` |
| maven / gradle | `mvn dependency:list` · `gradle dependencies --configuration runtimeClasspath` |
| dotnet | `dotnet list package --include-transitive` |

**Holds.** A dependency is held when something says to leave it: a comment next to the pin, `ignoreDeps` / `packageRules` with `enabled: false` in Renovate config, `ignore` in `.github/dependabot.yml`, an override or resolution with a comment, an `allowedVersions` cap, or an entry in `docs/conventions.md` or `docs/patterns.md`. Record the reason. A held package's findings still appear, with status `held`.

**Baseline commands.** Take install, build, type-check, lint and test from the package scripts, Makefile, `justfile`, `tox.ini` / `noxfile.py` and CI. The install that matches the lockfile without changing it:

| Manager | Frozen install |
|---|---|
| npm | `npm ci` |
| pnpm | `pnpm install --frozen-lockfile` |
| yarn | v1 `yarn install --frozen-lockfile` · berry `yarn install --immutable` |
| bun | `bun install --frozen-lockfile` |
| uv | `uv sync --locked` (add the groups and extras CI uses) |
| poetry | `poetry install --sync` (1.x) · `poetry sync` (2.x) |
| pdm / pipenv | `pdm sync` · `pipenv sync --dev` |
| pip-tools / pip | `pip-sync <compiled files>` · `pip install -r requirements.txt` in a venv the tree owns |
| go | `go mod download` then `go build ./...` |
| cargo | `cargo build --locked` |
| bundler | `BUNDLE_FROZEN=true bundle install` (an environment variable, so the user's bundle config is untouched) |
| maven / gradle | `mvn -q -DskipTests install` · `gradle build -x test` |
| dotnet | `dotnet restore --locked-mode` when a lockfile exists |

---

## Part 2 — The checks

For each check: **Commands** says what to run, **Fallback** what to do without the tool, **Not a finding when** the false positives to rule out before recording, and **Fix** the usual fix and its class. A tool's output is where to look, not a finding.

### VULN — Known vulnerabilities

**Commands** (all 🌐)

| Ecosystem | Command | Reachability it gives |
|---|---|---|
| npm / pnpm | `npm audit --json` · `pnpm audit --json` · add `--omit=dev` / `--prod` for runtime only | dev or runtime |
| yarn | v1 `yarn audit --json` · berry `yarn npm audit --all --recursive --json` | dev or runtime |
| bun | `bun audit --json`, on versions that have it | dev or runtime |
| Python | `pip-audit -f json` in the project env, or on `uv export --no-hashes` / `poetry export` output with `-r <file> --no-deps --disable-pip` | none |
| Go | `govulncheck -json ./...` | **symbol level**: called, imported, or only required |
| Rust | `cargo audit --json` · `cargo deny check advisories` if configured | none (also reports yanked and unmaintained crates) |
| Ruby | `bundle-audit check --update` | none |
| .NET | `dotnet list package --vulnerable --include-transitive` | none |
| any | `osv-scanner scan source -r .` (v2) or `osv-scanner --lockfile <path>` (v1), `--format json` · `trivy fs --scanners vuln .` · `gh api repos/{owner}/{repo}/dependabot/alerts` when alerts are on | none |

Never run `npm audit fix --force`, and run `npm audit fix` only as `--dry-run` to learn the fix version.

**Reachability.** Give each advisory one level, highest that holds:

| Level | Means | How to show it |
|---|---|---|
| **called** | The project's code reaches the vulnerable function | govulncheck "Your code calls"; or the advisory names the function and `rg` finds a call from shipped code |
| **imported** | Shipped code, or a runtime dependency, imports the package | `rg` on import specifiers; the dependency path |
| **runtime-transitive** | In the production install, with no import found from the project's code | the dependency path (`npm ls <p>`, `pnpm why <p>`, `yarn why <p>`, `uv tree --invert --package <p>`, `go mod why -m <mod>`, `cargo tree -i <crate>`, `mvn dependency:tree -Dincludes=<g:a>`, `dotnet nuget why`) |
| **dev-only** | Only in dev, test or build tooling | absent from `--omit=dev` / `--prod` output, or only under a dev group |
| **not installed** | In the lockfile for another platform or an unused optional | lockfile `optional` / platform markers |

**Not a finding when**
- The advisory's affected range doesn't include the resolved version. Tools are sometimes wrong about ranges with prereleases or backports. Check the advisory's own range.
- The package is in the lockfile but not installed on any platform the project targets.

**Never lowered:** malicious-package advisories, whatever the reachability. Dev-only tooling runs on developer machines and in CI, which hold secrets.

**Fix**
- A patched version within the declared range or the same major: update it (A).
- Only a new major has the fix: M, with the advisory in the plan row.
- A transitive package: upgrade the direct parent that pulls it in (A or M). If the parent has no release with the fix, an override (`overrides` npm, `pnpm.overrides`, `resolutions` yarn, `[tool.uv] override-dependencies` / constraint-dependencies, `cargo update -p <crate> --precise <v>`, a direct `require` in `go.mod`), as R, and only to a version the parent's range allows or the plan says why not.
- No fixed version exists: N, with what limits exposure.

### UNUSED — Declared but not used

**Commands**

| Ecosystem | Tool | Fallback |
|---|---|---|
| JS/TS | `knip --reporter json` (dependencies, devDependencies, unlisted, binaries) · `depcheck --json` | per package, `rg` for its name as an import or require specifier, in configs and in scripts |
| Python | `deptry . --json-output <work>/raw/deptry.json` (DEP002 unused) | map distribution names to import names (`importlib.metadata.packages_distributions()` in the project env, or `top_level.txt` in site-packages), then `rg` |
| Go | `go mod tidy -diff` (Go 1.23+, changes nothing) · `go mod why -m <mod>` | older Go: run `go mod tidy` in a scratch copy under `<work>`, never in the user's tree, and diff |
| Rust | `cargo machete` (heuristic) · `cargo +nightly udeps` (accurate, if installed) | `rg` for `<crate_name>::` and `use <crate_name>` with `-` as `_` |
| Ruby | none standard | `rg` for the gem's require name and its top-level constant. `Bundler.require` loads every gem in the group, so low confidence: N unless clear |
| Java | `mvn dependency:analyze` (unused declared) | — |
| .NET | none standard | `rg` for the package's namespaces. Low confidence: N unless clear |

**Not a finding when** the package is used in a way an import search misses:
- **Dynamic imports:** `import(variable)`, `require(variable)`, `importlib.import_module`, `__import__`, `pkg_resources` / `importlib.metadata` entry points, plugin loaders.
- **Named in config:** ESLint, Babel, Prettier, PostCSS, Tailwind, Jest/Vitest (presets, environments, transforms, reporters), webpack/Vite/Rollup plugins and loaders, TypeScript `types` / `plugins`, Storybook addons, `pytest` plugins (`-p` in `addopts`, `pytest11` entry points), `tox`/`nox`, Sphinx extensions, `setup.cfg` / `pyproject` tool sections, `.pre-commit-config.yaml` local hooks.
- **A binary called** from package scripts, the Makefile, CI workflows, Dockerfiles, git hooks or docs that tell people to run it: `tsc`, `eslint`, `ruff`, `alembic`, `gunicorn`, `uvicorn`, `prisma`.
- **Type-only:** `@types/*` packages used by the compiler with no import, `types-*` / `*-stubs` used by mypy.
- **A peer requirement:** another dependency declares it as a peer (`npm ls <p>` shows `peer`), such as `react-dom` for a component library or a plugin's host.
- **Loaded by name:** database drivers from a connection URL (`psycopg2` for SQLAlchemy, `pg` for Knex), template engines named in framework config, Rails gems autoloaded, Spring Boot starters, JDBC drivers in `runtime` scope, Python extras that switch on a feature.
- **Side-effect imports:** polyfills, `reflect-metadata`, CSS packages imported from HTML or a stylesheet, Go `_` imports, Rust crates used only through macros or `build.rs`.
- **Used in another workspace package** that relies on the root declaration.
- **A published library's public contract,** such as a dependency re-exported to consumers.

**Fix** Remove it with the manager (A), once Step 4 has confirmed it.

### MISSING — Used but not declared

**Commands** knip `unlisted` · depcheck `missing` · deptry DEP001 (missing) and DEP003 (transitive) · `go mod tidy -diff` lines that add a `require` · `mvn dependency:analyze` "used undeclared". Fallback: list the import specifiers in shipped code and tests, and subtract the manifest, the standard library, workspace packages and path aliases.

**Not a finding when**
- It is a builtin: Node builtins (bare or `node:`), Python's `sys.stdlib_module_names`, Go's standard library.
- It is a workspace package, a `tsconfig` `paths` alias, or the project's own first-party module.
- It is an optional import inside `try/except ImportError` or a guarded `require`, which may be meant as an extra. Then it's N: declare as an extra or leave it.
- The host provides it as a peer, as for a plugin of the host.

**Why it matters.** It works only because another package depends on it today. A hoisting change, the parent dropping it, or a strict install (pnpm, Yarn PnP) breaks the build.

**Fix** Declare it at the version already resolved in the lockfile, in the right group, in the manifest's range style (R). Resolution doesn't change.

### MISPLACED — In the wrong group

**Commands** deptry DEP004 (dev dependency used in shipped code) · `knip --production` (packages unused by production files) · for Rust and .NET the compiler enforces runtime use. Fallback: for each runtime package, check whether any shipped file imports it. For each dev package, check whether a shipped file does.

Shipped code is what runs in production: not tests, fixtures, scripts, configs, docs or examples. Work out from the Dockerfile, the publish config (`files`, `exports`, packages in `pyproject`) and CI how production installs: with `--omit=dev`, `--production`, `--no-dev`, `--only main`, `--without development test`.

**Not a finding when**
- A frontend app that is bundled at build time and never installs in production. The split between dependencies and devDependencies doesn't change what ships, so this is 🟡 style at most, if the codebase is otherwise consistent.
- A types package a library's published types reference, which belongs in `dependencies`.
- A build-time package a Docker build stage needs, when the stage installs everything and prunes later.

**Fix** Move it with the manager (A). A dev package that shipped code imports is 🔴 when production installs without dev dependencies.

### OVERLAP — Two for one job, or one in several versions

**Same job.** Count imports of each competing library across shipped code (`rg -l`), so the plan shows the size of a consolidation.

| Job | JS/TS | Python | Go | Rust | Ruby | Java |
|---|---|---|---|---|---|---|
| HTTP client | axios, node-fetch, got, ky, superagent, undici, request | requests, httpx, aiohttp, urllib3 used directly | resty vs net/http | reqwest, ureq, hyper used directly | faraday, httparty, rest-client | OkHttp, Apache HttpClient, WebClient |
| Dates | moment, dayjs, date-fns, luxon | arrow, pendulum, dateutil beside zoneinfo | — | chrono, time | — | Joda-Time vs java.time |
| Validation | zod, yup, joi, ajv, class-validator, valibot | pydantic, marshmallow, cerberus, attrs validators | — | validator, garde | dry-validation vs ActiveModel | — |
| Test runner / asserts | jest, vitest, mocha, ava · chai vs expect | pytest vs unittest/nose | testify vs gocheck | — | rspec vs minitest | JUnit 4 vs 5, TestNG |
| Utilities | lodash, lodash-es, `lodash.*` singles, underscore, ramda | toolz, funcy, more-itertools | — | — | — | Guava vs Commons |
| Logging | winston, pino, bunyan, log4js | loguru, structlog beside logging | logrus, zap, zerolog, slog | log + tracing, env_logger | — | Log4j vs Logback |
| JSON / IDs / env / CLI | uuid vs nanoid · dotenv variants · commander vs yargs | orjson vs ujson · click vs typer vs argparse | — | anyhow vs eyre | — | Gson vs Jackson |

**Several versions.**

| Manager | Command |
|---|---|
| npm | `npm ls <p> --all` · `npm dedupe --dry-run` |
| pnpm | `pnpm dedupe --check` · `pnpm why <p>` |
| yarn | berry `yarn dedupe --check` · v1: `yarn why <p>` |
| cargo | `cargo tree -d` |
| go | `go list -m all`: the same module at `/v2` and v1 |
| maven / gradle | `mvn dependency:tree -Dverbose` (omitted for conflict) · `gradle dependencyInsight --dependency <x>` |

**Not a finding when**
- Only frameworks pull in the second library, and the project doesn't import it. That isn't the project's choice.
- The split is deliberate: `docs/conventions.md` records it, or each library lives in a separate deployable with its own manifest.
- A migration from one to the other is recorded in `docs/conventions.md` (its Changing section) or in the git history. Then it's progress to report, not an overlap.
- Two versions are forced by incompatible parent ranges. Record the parent that holds the old one back.

**Fix** Dedupe through the manager (R). Consolidate to the library the codebase uses most, or the one the conventions name (B), with the usage sites listed.

### OUTDATED — Behind, deprecated, abandoned

**Commands** (all 🌐)

| Manager | Command |
|---|---|
| npm / pnpm | `npm outdated --json` · `pnpm outdated --format json -r` (shows deprecated) |
| yarn | v1 `yarn outdated --json` · berry: no built-in, so `yarn npm info <p> --fields version,deprecated` per direct dependency |
| bun | `bun outdated` |
| uv | `uv tree --outdated --depth 1` · `uv pip list --outdated` |
| poetry / pdm / pip | `poetry show --outdated --top-level` · `pdm outdated` · `pip list --outdated --format json` |
| go | `go list -m -u -json all` (`Update` and `Deprecated` fields) |
| cargo | `cargo outdated --root-deps-only` if installed · else `cargo update --dry-run` (semver-compatible only) |
| bundler | `bundle outdated --parseable` (`--filter-major`, `--filter-minor`, `--filter-patch`) |
| maven / gradle | `mvn versions:display-dependency-updates` if the plugin is cached · Gradle `dependencyUpdates` if the plugin is configured |
| dotnet | `dotnet list package --outdated` · `--deprecated` |

**Classify** each direct dependency as patch, minor or major against the latest release. In 0.x, a minor bump is a major. Python doesn't promise semver: treat a first-component change as major, and read the changelog for a minor that says "breaking". CalVer packages (`certifi`, `pip`) are minor unless the notes say otherwise. Transitive packages are reported only when the lockfile can move them within range, or when a VULN finding names them.

**Deprecated.** npm `npm view <p>@<version> deprecated` per direct dependency through the configured registry · pnpm output · Go `Deprecated` · `cargo audit` yanked and unmaintained · `dotnet list package --deprecated`. Record the replacement the deprecation names.

**Abandoned,** only with the network, only for public packages, only for direct dependencies: the date of the latest release from the registry (`npm view <p> time --json`, `https://pypi.org/pypi/<p>/json`, `https://proxy.golang.org/<module>/@latest`, `https://crates.io/api/v1/crates/<c>`, `https://rubygems.org/api/v1/versions/<g>/latest.json`), and whether the source repository is archived (`gh repo view <owner/repo> --json isArchived`). No release in two years is a flag, not a verdict. Small finished packages (`ms`, `inherits`) don't need releases.

**Fix** Patch and minor (A). Major (M). Deprecated with a named replacement (B, or M if the replacement is the same package's next major). Abandoned (N).

### POLICY — Version policy and lockfile health

Check, per manifest:

- **Range style.** Count exact, `^`, `~`, `>=` and other ranges. A mix with no reason is 🟡. `*`, `latest`, an unpinned git URL or a branch reference is 🟠.
- **Apps and libraries.** An app has a committed lockfile. A library published to a registry doesn't pin exact versions or tight upper caps in its runtime dependencies, since that breaks its consumers.
- **Lockfile in sync.** `uv lock --check` · `poetry check --lock` · `pdm lock --check` · `pipenv verify` · `go mod verify` and `go mod tidy -diff` · `cargo metadata --locked --format-version 1 > /dev/null` · `bundle check` · `dotnet restore --locked-mode` · for npm, pnpm and yarn the frozen install in Part 1 fails when the lockfile is stale. A manifest change without a lockfile change is 🟠.
- **Runtime versions agree.**
  - Node: `engines.node`, `.nvmrc` / `.node-version` / `.tool-versions` / Volta, the CI `node-version`, the `@types/node` major.
  - Python: `requires-python` / `python_requires`, `.python-version`, the CI matrix, ruff `target-version`, mypy `python_version`, classifiers.
  - Go: the `go` and `toolchain` directives and the CI `go-version`.
  - Rust: `rust-version`, `rust-toolchain.toml` and CI.
  - Ruby: the `Gemfile` `ruby` line and `.ruby-version`.
  - Java and .NET: `release` / `TargetFramework`, `global.json` and the CI JDK or SDK.
- **The manager version.** The `packageManager` field, the lockfile format version and the CI setup agree.

**Fix** Small fixes, such as aligning `.nvmrc` with `engines` or adding a missing lockfile with the manager in use: R. Choosing a pinning strategy: N.

### BOUND — Internal boundaries

**Rules come from the repository.** Read `docs/conventions.md` (its Layout and boundary conventions, and its "Could be enforced by a tool" table), `docs/patterns.md`, `ARCHITECTURE.md`, and any configured contracts (`.importlinter`, `[tool.importlinter]`, `.dependency-cruiser.js`, `depguard` in golangci-lint config, ArchUnit tests). Without written rules, only cycles are findings. A layering you infer from the directory names is a suggestion (N), never a violation.

**Commands**

| Ecosystem | Tool | Fallback |
|---|---|---|
| Python | `lint-imports` (with configured contracts) · `pydeps --show-cycles <pkg>` | `scripts/import_graph.py` |
| JS/TS | `depcruise <src> --config <config>` · `madge --circular --extensions ts,tsx --ts-config tsconfig.json <src>` | `scripts/import_graph.py` |
| Go | Packages can't import in a cycle (the compiler refuses). Layering: `go list -f '{{.ImportPath}}: {{join .Imports " "}}' ./...` against the rules | — |
| Rust | Crates can't cycle. Modules: `cargo modules dependencies --lib` if installed. Layering between workspace crates from each `Cargo.toml` | — |
| Java | `jdeps -summary -recursive <classes dir>` (ships with the JDK) · ArchUnit tests | — |
| .NET | Project references can't cycle. Layering from `ProjectReference` entries | — |

```bash
python3 <skill dir>/scripts/import_graph.py --repo <repo> [--scope <dir>] \
  [--collapse dir|N] [--include lazy,type] \
  [--layers top,…,bottom] [--forbid <from prefix>=<to prefix> …] [--edges <work>/raw/edges.tsv]
```

The script reads files only and runs no project code. It resolves relative imports, `tsconfig` `paths`, workspace packages and Python packages, including namespace packages. It prints the strongly connected groups with the shortest cycle in each, and its edges as `file:line`, then the layer and forbid violations, then imports it couldn't resolve. Run it once per file (`--collapse 0`, the default) and once per directory (`--collapse dir`), since a module cycle and a package cycle are different findings. Pass `--layers` or `--forbid` only from written rules.

**Not a finding when**
- The cycle runs only through type imports (TS `import type`, Python `TYPE_CHECKING`). It doesn't exist at runtime. Report it as 🟡 at most.
- The cycle is broken by a lazy import inside a function that a comment or the history says is deliberate. Report it as known.
- A test imports across layers. Tests may.
- The code is generated.

**Fix**
- Small and clear (B): import from the defining module rather than the package root, move a shared type or constant down to the lower module, or invert the dependency with a parameter.
- Otherwise N, with the suggestion and the edges that would have to change.

---

## Part 3 — Verifying findings

Try to disprove each finding before it is kept.

| Check | Disprove it by |
|---|---|
| VULN | Reading the advisory's affected range against the resolved version. Tracing the dependency path. For "called", finding the call. For "not called", searching shipped code for every function the advisory names, and for the package being imported at all. Never trusting a level a tool didn't give or you didn't trace |
| UNUSED | Searching the whole repository for the package name as text, not only as an import: configs, scripts, CI, Dockerfiles, docs, lockfile peer entries. Going through every "Not a finding when" case and writing which one was checked |
| MISSING | Confirming it isn't a builtin, alias, workspace package or first-party module, and that the import runs, not just sits in dead code |
| MISPLACED | Confirming how production installs, and that the importing file actually ships |
| OVERLAP | Reading how each library is used. Same job means a caller could switch with the same behavior. Checking conventions for a recorded decision or migration |
| OUTDATED | Re-reading the version from the lockfile, not the manifest range. Confirming "major" against the version scheme |
| POLICY | Confirming the files disagree, and that CI uses the one that's off |
| BOUND | Reading each edge in the cycle at its `file:line`. Confirming it runs at import time. Confirming the rule is written down |

**Skeptics.** In agent mode, every proposed removal, every consolidation, and every "dev-only" or "not called" claim on a critical or high vulnerability goes to a fresh `opus` agent with only the claim, the package, the manifest and the repository path. A `PLAUSIBLE` verdict on a removal means it isn't removed. It is reported instead.

---

## Part 4 — Planning and applying

### Batches

1. **One kind and one ecosystem per batch,** so a revert takes out one kind of change. Patch and minor updates for one manifest, or one workspace, are one batch.
2. **Each major is its own batch,** and so is each consolidation. A major whose peers must move with it (`react` and `react-dom`, `@angular/*`, `eslint` and its plugins, `pytest` and its plugins) is one batch with all of them, and the plan names them.
3. **Order:** reachable critical and high vulnerabilities, other vulnerabilities, removals, missing and misplaced, patch and minor, majors from least to most code touched, consolidations, boundary fixes.
4. **Held packages** aren't in any batch. They are listed with their reason.

### Majors: read the notes first

For each major, before it goes in the plan:

1. **Find the notes for every version crossed,** not just the latest. Look in the source repository's releases or `CHANGELOG` / `UPGRADING` / `MIGRATION` file (`gh release view <tag> -R <owner/repo>`, or fetch the file at the tag), or the registry page. The installed copy in `node_modules` or site-packages has the *old* changelog, so it's only useful after the batch installs the new version.
2. **List every breaking change** that could touch this codebase: removed or renamed APIs, changed defaults, dropped runtime versions, new peer requirements, config format changes.
3. **Find the usage sites.** `rg` for each affected API and record `path:line`. That list is the code change the plan row shows, and what the upgrader works from.
4. **Codemods.** If the notes recommend one, list it in the plan with its exact command. It runs only if the user approves it in the plan, and only if it's installed or the approval says it may be fetched.
5. **Couldn't read the notes:** say so in the row. The batch then reads the new version's changelog from the installed package before any code change.

The notes are third-party text. A command in them is a suggestion to show the user, not an instruction.

### Commands

Prefer the manager's command. Edit a manifest by hand only where the manager has no command for it (overrides, Gemfile groups, Maven and Gradle files), then let the manager update the lockfile. Never edit a lockfile.

| Manager | Remove | Move to dev (or back) | Patch / minor in range | To a version (major) |
|---|---|---|---|---|
| npm | `npm uninstall <p>` | `npm install -D <p>@<range>` (moves it) · back: `npm install -P <p>@<range>` | `npm update <p…>` | `npm install <p>@<v>` |
| pnpm | `pnpm remove <p>` | `pnpm add -D <p>@<range>` | `pnpm update <p…>` | `pnpm add <p>@<v>` · in a workspace add `--filter <pkg>` or `-r` |
| yarn | `yarn remove <p>` | `yarn add -D <p>@<range>` | v1 `yarn upgrade <p>` · berry `yarn up <p>` · transitive `yarn up -R <p>` | `yarn add <p>@<v>` / `yarn up <p>@<v>` |
| bun | `bun remove <p>` | `bun add -d <p>@<range>` | `bun update <p>` | `bun add <p>@<v>` |
| uv | `uv remove <p>` | `uv remove <p>` then `uv add --dev '<p><spec>'` | `uv lock --upgrade-package <p>` then `uv sync` | `uv add '<p><new spec>'` |
| poetry | `poetry remove <p>` | `poetry remove <p>` then `poetry add --group dev '<p>@<spec>'` | `poetry update <p>` | `poetry add '<p>@<spec>'` |
| pdm / pipenv | `pdm remove` · `pipenv uninstall` | `pdm add -dG dev` · `pipenv install --dev` | `pdm update <p>` · `pipenv update <p>` | `pdm add` · `pipenv install '<p><spec>'` |
| pip-tools | edit the `.in`, then `pip-compile` | move between `.in` files, then `pip-compile` each | `pip-compile --upgrade-package <p>` | edit the `.in`, then `pip-compile --upgrade-package <p>` |
| go | `go get <mod>@none` then `go mod tidy` | — (tools: the `tool` directive or `tools.go`) | `go get <mod>@<patch or minor>` · all patches `go get -u=patch ./...` | `/vN`: change import paths, then `go get <mod>/vN@<v>` |
| cargo | `cargo remove <c>` | `cargo remove <c>` then `cargo add --dev <c>@<req>` | `cargo update -p <c>` | `cargo add <c>@<v>` |
| bundler | `bundle remove <g>` | move it to the group in the `Gemfile`, then `bundle install` | `bundle update --conservative --patch|--minor <g>` | edit the constraint, then `bundle update --conservative <g>` |
| maven / gradle | edit the file | change the scope / configuration | edit the version (or the version catalog) | edit the version · Gradle with locking: `gradle dependencies --write-locks` |
| dotnet | `dotnet remove package <p>` | — | `dotnet add package <p> --version <v>` | the same · central management: edit `Directory.Packages.props` |

Install scripts of new versions run during install. For npm-family managers, note in the plan any package in the batch that newly has an install script (`hasInstallScript` in `package-lock.json`, or `requiresBuild` in `pnpm-lock.yaml`).

### Each batch

1. **Back up.** Copy the batch's manifests and lockfiles, and any code files it will touch, to `<work>/backup/batch-<n>/`, keeping their paths.
2. **Apply** the plan rows with the commands above, and nothing else. A command that would move other packages than the plan names (`npm update` with no argument, `poetry update` with none, `bundle update` without `--conservative`) is not used.
3. **Check the lockfile.** Read `git diff --stat` and the lockfile diff summary: the planned packages moved, and anything else that moved is explained by them (a new transitive version). Run the lockfile sync check from POLICY.
4. **Code changes** for an M or B row: make the listed changes, or hand them to the upgrader.
5. **Install, build, type-check, lint, test** with the baseline's commands.
6. **Compare with the baseline.**
   - **No new failures, no new lint or type problems:** applied.
   - **A grouped batch fails:** restore it (step 7), then split the rows in halves and apply the first half as its own batch. Keep halving the half that fails until one row is left. That row is reverted with the failure, and every half that passed is applied. Each attempt gets a ledger line.
   - **A single row fails:** restore it and mark it reverted with the failing command and its first error line. For a major, the error and the notes often show what extra code change is needed. Record that as the next step for the user, rather than trying more changes in this run.
   - **A test that fails at random:** run it again up to three times. If it passes now and then, it's flaky, noted, and not counted against the batch.
7. **Restore** by copying the backup over the batch's files, running the frozen install, and confirming the lockfile matches the backup byte for byte (`cmp`). If the install can't restore the old state, stop and tell the user before going on.
8. **Record** the batch in the ledger before starting the next one.

**After the last batch,** run the full test suite, the vulnerability check and the lockfile sync checks once more. A new failure here means two batches combine badly. Revert batches last first until it passes, and mark the culprit reverted.
