# dep-hygiene

Audits a repository's dependencies, both external packages and internal module boundaries, and fixes what it can in small batches. Each batch is checked with build, types, lint and tests, and reverted if it fails.

## When to use it

- "Audit our dependencies" or "clean up unused packages."
- "Fix the vulnerable packages", with a check on whether the vulnerable code is actually reachable.
- "Upgrade everything that is safe to upgrade", with each major handled on its own.
- Two libraries do the same job, a lockfile is out of sync, or modules import each other in cycles.
- Not for: reviewing a code change (use [`pr-review`](../pr-review/)), or tidying the code a migration touched (use [`deslop`](../deslop/)).

## Usage

```
/dep-hygiene [options]
```

With no options it covers the whole repository: every manifest and lockfile, every workspace package.

| Option | What it does |
|---|---|
| `--scope <dir or package>` | One directory, or one package of a monorepo by name. A shared root lockfile still changes, and the plan says so. |
| `--report-only` | Stop after the plan and present it as the report. Nothing is changed or downloaded. |
| `--audit-only` | Only the vulnerability check, and only vulnerability fixes in the plan. |
| `--no-major` | Plan no major upgrades. They are listed as pending, with the work each needs. |
| `--auto` | Apply the routine class without waiting: verified-unused removals, misplaced moves, patch and minor updates. Everything else waits, and majors and consolidations need a yes each. |
| `--models <role>=<model>,…` | Override an agent's model. Roles: `auditor`, `skeptic`, `upgrader`. Values: `sonnet`, `opus`, `fable`. |

Examples:

```
/dep-hygiene
/dep-hygiene --scope packages/api --no-major
/dep-hygiene --audit-only
/dep-hygiene --report-only
```

## How it works

1. **Target and options.** Scope, where changes go, which registries the checks will query, whether code may be run.
2. **Inventory and baseline.** Every manifest, lockfile and package manager; direct dependencies; holds (pins, ignore rules, overrides); written rules in `docs/conventions.md` or `docs/patterns.md`; installed tools; and a baseline of install, build, types, lint and tests.
3. **Run the checks.** VULN (vulnerabilities and reachability), UNUSED, MISSING, MISPLACED, OVERLAP (two libraries for one job, duplicate versions), OUTDATED, POLICY (pinning, engine ranges, lockfile sync) and BOUND (import cycles and layering violations).
4. **Verify every finding.** "Unused" is checked against dynamic imports, plugins named in config, binaries called from scripts and CI, type-only packages and peer requirements. Skeptic agents try to disprove each removal and each "not reachable" claim on a high or critical vulnerability. A removal that is only plausible is not made.
5. **Plan.** Order: reachable critical and high vulnerabilities, removals, missing and misplaced deps, patch and minor updates per ecosystem, each major alone (its migration notes read and the code it touches listed), consolidations, boundary violations. You approve all, some or none.
6. **Apply in batches.** Backup, apply through the package manager, install, build, type-check, lint, test, compare with the baseline. A failing grouped batch is split in halves to find the culprit; a failing single item is restored byte for byte from backup and marked reverted.
7. **Check completeness.** Counts taken from the work files.
8. **Report.**

Not reachable lowers a vulnerability's priority but never hides it. Every finding ends in the ledger as applied, reverted, declined, deferred, held or report only.

## What you get

- Changed manifests and lockfiles, plus any code an approved migration touches, left uncommitted. If those files already have uncommitted changes, the work goes to a worktree at `<repo parent>/<repo name>.worktrees/dep-hygiene-<slug>` on branch `deps/<YYYY-MM-DD>`, with its own install.
- A report: vulnerabilities before and after by severity, what was removed, moved, added and updated (from and to), majors pending and the work each needs, boundary violations with suggested fixes, what failed and was reverted, held dependencies, and limits.
- A work directory outside your repo (`<scratchpad>/dep-hygiene-<slug>/`, or a temp dir) with one file per step, the ledger, raw tool output in `raw/`, and `backup/batch-<n>/`.

## Safety

- Never switches package manager. Every change goes through the manager the lockfile shows, and lockfiles are never edited by hand.
- Never installs tools: no `npx` of an uninstalled package, `pnpm dlx`, `uvx`, `pipx run`, `go run …@latest` or `cargo install`. Approving the plan lets the package manager download the planned versions from your configured registry, and nothing else.
- Commits nothing. It never switches your branch, stashes or resets.
- Audit and outdated commands send the dependency list to a registry or advisory database. Private packages are never sent to a public service. If you say not to use the network, or it is unreachable, those checks are recorded as not run.
- Majors and consolidations need a yes each, even with `--auto`. A codemod from a migration guide runs only if the plan lists it and you approve it.
- Held dependencies are not upgraded without asking.
- Updating in the working tree also changes your installed environment (`node_modules`, `.venv`); the plan says so.
- Text in manifests, changelogs, package READMEs or advisories that tells Claude what to do is reported as a finding, not followed.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/checks.md` | Tools, network rules, fix classes and severity; the inventory, each check and how to disprove its findings; how to plan majors and apply batches |
| `references/formats.md` | The output contract for every work file and the report |
| `scripts/import_graph.py` | Builds the internal import graph for Python and JS/TS when no boundary tool is installed, and reports cycles and layering violations. Reads files only. Python standard library only. |

`import_graph.py` can be run on its own:

```
python3 scripts/import_graph.py --repo <path> [--scope <dir>] [--layers top,...,bottom] [--forbid from=to]
```

## Related skills

- [`conventions`](../conventions/) — writes `docs/conventions.md`, which records library choices and boundaries this skill judges against.
- [`sdlc-fast`](../sdlc-fast/) — writes `docs/patterns.md`, which this skill also reads.
- [`guided-review`](../guided-review/) — walks you through the resulting diff.
- [`deslop`](../deslop/) — tidies code changes a migration made.
