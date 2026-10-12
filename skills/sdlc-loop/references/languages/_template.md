# <Language>

Copy this file to `<language>.md` (lowercase, e.g. `go.md`, `rust.md`) and fill it in. Keep it near 100 lines: agents read it every iteration, so it should hold what is specific to this language and easy to get wrong, not a style guide. Add the new file to the list under Language practices in `SKILL.md`.

Keep this first paragraph in every language file:

This is the lowest-ranked standard. The user's patterns, the project's rules and config, and the code around the change all override it. Use it where they are silent.

## Tooling

How to tell which tools and package manager the project uses, and which version of the language it targets.

| Job | Common tools |
|---|---|
| Format | |
| Lint | |
| Types | |
| Tests | |
| Coverage | |
| Dependency audit | |
| Static security | |

## Idioms and structure

Ten or so entries. How well-written code in this language handles errors, data modelling, resources, concurrency and module layout. Leave out anything the formatter or linter already settles.

## Common bug sources

The mistakes this language makes easy, each specific enough to look for in a diff: the construct, and what goes wrong.

## Security pitfalls

The unsafe APIs and defaults of the language and its common libraries, each with the safe alternative.

## Testing conventions

The framework's idioms: fixtures, parametrized cases, asserting on errors, faking time and the network, and how tests are named and laid out.

## Edge cases to always try

Inputs and conditions that behave surprisingly in this language's types: empty and missing values, numeric limits, text encoding, dates, concurrency.
