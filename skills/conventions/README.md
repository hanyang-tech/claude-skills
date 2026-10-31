# conventions

Works out how a codebase is actually written and records it in `docs/conventions.md`. Each convention comes with a count of how widely it holds, an example file and, where one exists, a file that breaks it. You also get a list of helpers to reuse and the areas where the code disagrees with itself.

## When to use it

- "Write down how we do things in this repo" or "document our coding standards".
- You want a conventions file or a `CLAUDE.md` so new people, and agents, stop guessing.
- A new contributor keeps writing code that works but doesn't look like the rest of the codebase.
- You want to know which style is the real one when the code uses two, with numbers.
- The conventions doc has gone stale and needs re-measuring.
- Not for: bringing recent code in line with conventions that already exist ([`deslop`](../deslop/) does that, with `--families DRIFT`). This skill writes the conventions down; it doesn't change code.

## Usage

```
/conventions [options]
```

With no options it studies the whole repository and writes `docs/conventions.md`. If that doc already exists, it refreshes it instead.

| Option | What it does |
|---|---|
| `--scope <dir>` | Study one package or app in a monorepo. The doc goes in that directory's `docs/` unless `--out` is given |
| `--out <path>` | Where to write the doc. Default `docs/conventions.md`, or the existing conventions doc |
| `--update` | Re-measure every convention in an existing doc, keep its IDs and report what changed. This is the default when the doc exists |
| `--auto` | Don't ask about mixed areas; record them as mixed and list them in the report |
| `--models <role>=<model>` | Override an agent's model. Roles: `extractor`, `skeptic`. Values: `sonnet`, `opus`, `fable` |

Examples:

```
/conventions
/conventions --scope apps/api
/conventions --update --auto
```

## How it works

1. **Scope** - find the languages, areas, written rules (`CLAUDE.md`, `CONTRIBUTING.md`, `docs/patterns.md`, linter configs) and tool commands.
2. **Choose what to study** - rank files by authors, commits and age with `scripts/established.py`, then pick 20 to 40 established files across every area and layer, plus the shared helpers.
3. **Extract candidates** - read the sample against 15 topics (layout, naming, errors, validation, types, logging, config, data access, boundaries, concurrency, dependencies, comments, tests, library choices, git style).
4. **Count each one** - count how widely each candidate holds across the whole scope, with a command you can rerun or a sampled read of at least 15 sites. Label it established (80% or more), prevailing (60 to 80%) or mixed. Compare the last 90 days with the established files to spot migrations.
5. **Settle what's mixed** - ask you about the mixed areas, migrations and written rules the code ignores, one round of at most four questions. What you decide becomes a rule.
6. **Write the doc** - tools first, then conventions by topic, the reuse index, what's mixed, migrations, recommendations and what a lint rule could enforce.
7. **Check completeness** - count from the work files and check that every exemplar path and line still exists.
8. **Report** - where the doc is, the counts, the key conventions and what is still mixed.

On a larger codebase (over about 30k lines in scope) it launches `sonnet` extractor agents per topic group, and `opus` skeptics that try to find counter-examples to strong rules like "never" and "always". Smaller codebases are done inline.

Conventions describe what the code does, counted. Recommendations are kept in their own section, and a language default or anything the formatter enforces is left out.

## What you get

- `docs/conventions.md` (or the `--out` path), aiming for under about 250 lines.
- If a `CLAUDE.md` exists, a `## Conventions` section pointing at the doc. Nothing else in it changes. If there is none, it offers to create one and doesn't.
- Proposed lint rules, each with its count of existing violations.
- A work directory with the step files (`1-scope.md` to `7-coverage.md`) in `<scratchpad>/conventions-<repo name>/`, or a temporary directory.
- A report in the chat.

## Safety

- Commits nothing.
- Does not edit your linter config. Lint rules are proposed, and the violation counts come from a temporary copy of the config in the work directory.
- Adds only the pointer section to an existing `CLAUDE.md`, and does not create one.
- Extractors and skeptics edit nothing in the repository.
- Update mode keeps any convention you wrote or decided as written, and asks if the code now contradicts it.
- Asks before anything beyond the doc: promoting rules to `docs/patterns.md`, adding lint rules, creating `CLAUDE.md`, committing.

## Files

| File | What it is |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `references/topics.md` | The 15 topics, how to count and judge strength, and the format of the candidate and measurement files |
| `references/format.md` | Formats for the work files, the doc template, the `CLAUDE.md` pointer and the lint-rule table |
| `scripts/established.py` | Ranks tracked source files by authors, commits and age, lists recently added files, and warns when history is too thin to trust. Python standard library only |

Run the script on its own:

```
python3 scripts/established.py --repo <repo> [--scope <dir>] [--top N] [--recent-days D]
```

## Related skills

- [`sdlc-fast`](../sdlc-fast/) - enforces the `docs/patterns.md` file that decided conventions can be promoted into. [`sdlc-loop`](../sdlc-loop/) uses the same file.
- [`deslop`](../deslop/) - `/deslop --families DRIFT` brings recent code in line with the doc.
- [`guided-review`](../guided-review/) - another reader of the doc.
- [`hotspots`](../hotspots/) - uses the doc when planning a refactor, and suggests this skill when a repository has none.
