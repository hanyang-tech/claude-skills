# Python

This is the lowest-ranked standard. The user's patterns, the project's rules and config, and the code around the change all override it. Use it where they are silent.

## Tooling

Use what the project already has, run the way the project runs it (`uv run`, `poetry run`, `hatch run`, `make`, `tox`). The right-hand column is what to look for, and what to propose as a backlog item if a job has no tool.

| Job | Common tools |
|---|---|
| Format | `ruff format`, `black` |
| Lint | `ruff check`, `flake8`, `pylint` |
| Types | `mypy`, `pyright` |
| Tests | `pytest` (with `pytest-asyncio` or `anyio`, `hypothesis`), `unittest` |
| Coverage | `pytest --cov --cov-branch` |
| Dependency audit | `pip-audit` |
| Static security | `bandit`, ruff's `S` rules, `semgrep` |

Read the supported Python version from `requires-python` in `pyproject.toml` or `.python-version`, and don't use syntax or standard-library features newer than it.

## Idioms and structure

- Type hints on public functions, at the strictness the project already uses. `X | None` on 3.10 and later.
- Structured data crossing a module boundary is a dataclass, a pydantic model or a `TypedDict`, whichever the project uses, not a loose dict.
- `pathlib.Path` for paths. `with` for files, locks, connections and transactions.
- Raise specific exceptions and catch the narrowest one that you can handle. Chain with `raise NewError(...) from err`.
- `logging` with lazy arguments (`logger.info("loaded %s", name)`) in library and service code, not `print`.
- `Enum` or `Literal` for a closed set of values, not bare strings.
- Timezone-aware datetimes: `datetime.now(timezone.utc)`. `datetime.utcnow()` returns a naive value and is deprecated.
- Money is `Decimal` or an integer of minor units, never `float`.
- Absolute imports within the package, no wildcard imports, and no work done at import time.
- A comprehension for a simple transform; a loop once there is branching or a side effect.

## Common bug sources

- A mutable default argument (`def f(items=[])`) or a mutable class attribute, shared across calls or instances.
- A closure in a loop capturing the loop variable late (`lambda: i`).
- A truthiness test (`if not value`) where `0`, `""` or an empty collection is valid and only `None` means missing.
- `is` used to compare values.
- Mutating a list or dict while iterating over it. Aliased rows from `[[0] * n] * m`. A shallow copy where nested data is then changed.
- Naive and aware datetimes mixed, or local time stored as if it were UTC.
- Float equality, and float arithmetic on money.
- Async: a coroutine that is never awaited; a blocking call (`requests`, `time.sleep`, a sync database driver) inside `async def`; a task from `asyncio.create_task` whose reference is dropped, so it can be garbage-collected and its exception lost; `gather` with no decision about `return_exceptions`.
- `except Exception: pass`, a bare `except:`, or a `return` inside `finally`, each of which hides an error.
- A generator or iterator consumed twice.
- `dict.get(key, default)` hiding a key that should have been there.
- `open()` without `encoding=`, which then depends on the platform.
- ORM: lazy loads inside a loop (N+1), and a session shared across threads or tasks.

## Security pitfalls

- SQL built with an f-string, `%` or `.format`, including inside ORM `text()` and raw queries. Use bound parameters.
- `subprocess` with `shell=True`, or a command string built from input. Pass an argument list.
- `pickle`, `marshal`, `yaml.load` (use `yaml.safe_load`), `eval` or `exec` on data that isn't trusted.
- User input joined into a file path. Resolve it and check it is still under the base directory. The same goes for member names when extracting `zipfile` and `tarfile` archives.
- HTTP calls with `verify=False`, or with no timeout (`requests` has none by default). A URL taken from the user is a request-forgery risk: restrict the hosts it may reach.
- `random` for tokens or IDs that must be unguessable (use `secrets`). `==` to compare secrets (use `hmac.compare_digest`).
- Secrets in logs, exception messages, or a model's `repr`.
- Jinja2 with autoescape off, `|safe` or `Markup` on user input, Django `mark_safe`.
- `assert` used for validation or an access check. Assertions are removed under `-O`.
- Passwords hashed with MD5 or SHA instead of argon2, bcrypt or scrypt.
- Untrusted XML parsed with the standard-library parsers (use `defusedxml`).
- Debug mode left on (`DEBUG = True`, Flask `debug=True`), and `tempfile.mktemp`.

## Testing conventions

- pytest style: plain `assert`, fixtures instead of `setUp`, `tmp_path` for files, `monkeypatch` for environment and attributes.
- `pytest.raises(SomeError, match="...")` for failures, so the test checks which error and not just that one happened.
- `pytest.mark.parametrize` for boundaries, with one case per boundary.
- Patch a name where it is looked up, not where it is defined. Prefer a small fake to a chain of mocks, and assert on results, not call counts, unless the call is the behavior.
- Inject the clock or freeze it (`freezegun`, `time-machine`). No `sleep` in tests.
- No network in unit tests: stub HTTP at the client (`respx`, `responses`, `pytest-httpx`).
- Name a test for the behavior: `test_refund_rejected_when_order_already_refunded`.

## Edge cases to always try

- `None`, `""`, a whitespace-only string, an empty list or dict, one element, duplicates.
- `0`, a negative number, a very large integer, `NaN` and infinity, and `True` where an integer is expected (`bool` is an `int`).
- Non-ASCII text, emoji, combining characters, mixed case; `bytes` where `str` is expected.
- Datetimes: naive against aware, a daylight-saving change, midnight, month and year ends, 29 February.
- JSON input with a missing key, an extra key, or the wrong type (`"1"` for `1`).
- An iterator passed where the code iterates twice.
- An external call that raises, times out, returns nothing, or returns a partial page.
- The same call made twice, and made concurrently, wherever module-level state or a cache is involved.
