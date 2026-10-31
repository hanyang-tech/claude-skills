#!/usr/bin/env python3
"""Rank a repository's source files by how much they cost to change.

A hotspot is a file that changes often (churn) and is hard to change
(complexity). Both come from one `git log --numstat` pass plus a read of each
file's current text. Read-only: runs git log and reads files, writes nothing.

Usage:
  hotspots.py [--repo PATH] [--scope DIR] [--since "12 months"] [--top N]
              [--min-coupling N] [--coupling-top N] [--max-commit-files N]
              [--tests] [--exclude GLOB ...] [PATH ...]
  hotspots.py --measure FILE ...        # complexity proxy only, no git

Columns (TSV):
  commits    commits in the window that touched the file (churn)
  bugfix     of those, commits whose subject matches fix|bug|hotfix|revert|regression
  authors    distinct authors in the window
  churned    lines added + deleted in the window
  lines      current non-blank, non-comment lines
  indent     sum of indentation depth over those lines (whitespace complexity)
  funcs      lines that open a function-like block of 2+ lines (approximate)
  max_func   longest such block, in lines (roughly the longest function)
  max_nest   deepest nesting inside one function, relative to its first line
  score      churn_n ** w * indent_n * (1 + bugfix_n); each _n is the value
             divided by the largest in scope; w = 1, or 0.5 for a young history

Coupling: pairs of files changed in the same commit at least --min-coupling
times. Commits touching more than --max-commit-files files (bulk renames,
formatting) are left out of coupling. share = together / min(commits of each).
"""
import argparse
import collections
import fnmatch
import os
import re
import subprocess
import sys
import time

SOURCE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java",
    ".kt", ".kts", ".scala", ".rb", ".php", ".cs", ".swift", ".m", ".mm", ".c",
    ".h", ".cc", ".cpp", ".hpp", ".ex", ".exs", ".erl", ".clj", ".dart", ".lua",
    ".sh", ".vue", ".svelte", ".sql",
}
SKIP_PARTS = {
    "node_modules", "vendor", "third_party", "dist", "build", "out", "target",
    "generated", "gen", "__generated__", ".venv", "venv", "migrations",
    "site-packages", "Pods", ".next", "coverage",
}
SKIP_SUFFIXES = (
    ".min.js", ".pb.go", "_pb2.py", "_pb2_grpc.py", ".g.dart", ".freezed.dart",
    ".generated.ts", ".d.ts", "_generated.go", ".gen.go",
)
TEST_PARTS = {"test", "tests", "__tests__", "spec", "specs", "testdata", "e2e",
              "testing", "fixtures", "__mocks__"}
TEST_NAME = re.compile(
    r"(^test_.*\.py$|_test\.(py|go)$|\.(test|spec)\.[cm]?[jt]sx?$|Tests?\.(java|kt|cs|swift)$"
    r"|_spec\.rb$|_test\.rb$|^conftest\.py$)"
)
BUGFIX = re.compile(r"(?<![a-z])(fix|bug|hotfix|revert|regression)", re.I)
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--|;|%)")
YOUNG_DAYS = 90
YOUNG_COMMITS = 50


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True,
        errors="replace",
    ).stdout


def is_test(path):
    parts = path.split("/")
    return bool(set(parts[:-1]) & TEST_PARTS) or bool(TEST_NAME.search(parts[-1]))


def is_source(path, excludes):
    if path.endswith(SKIP_SUFFIXES):
        return False
    if set(path.split("/")[:-1]) & SKIP_PARTS:
        return False
    if any(fnmatch.fnmatch(path, g) for g in excludes):
        return False
    return os.path.splitext(path)[1] in SOURCE_EXT


def rename_target(path):
    """numstat writes renames as 'a/{old => new}/b' or 'old => new'."""
    if "=>" not in path:
        return path, None
    m = re.match(r"^(.*)\{(.*) => (.*)\}(.*)$", path)
    if m:
        pre, old, new, post = m.groups()
        join = lambda mid: re.sub("//+", "/", pre + mid + post)
        return join(new), join(old)
    old, new = path.split(" => ", 1)
    return new, old


CONTROL = re.compile(
    r"^(if|else|elif|for|foreach|while|do|switch|case|match|when|catch|except|try|"
    r"finally|with|using|lock|return|await|yield|throw|raise|new|assert|unless|until|"
    r"select|defer|go)\b"
)
CONTAINER = re.compile(
    r"^((public|private|protected|internal|export|default|abstract|sealed|static|final|"
    r"partial|pub(\([a-z]+\))?|data|open)\s+)*"
    r"(class|struct|interface|enum|namespace|module|impl|trait|object|record|type|package)\b"
)
DEF_WORD = re.compile(r"(^|\s)(def|function|func|fn|sub|proc|defp?)\s")
CONTINUES = ("{", ")", "]")


def is_func_open(line):
    """A line that probably starts a function or method, in most languages."""
    if (not re.match(r"[\w$]", line) or line.endswith((";", ","))
            or CONTROL.match(line) or CONTAINER.match(line)):
        return False
    return bool(DEF_WORD.search(line)) or "=>" in line or bool(re.search(r"[\w>\]]\s*\(", line))


def measure(text):
    """Indentation-based complexity proxy for any language.

    lines      non-blank, non-comment lines
    indent     sum of indentation depth over those lines
    funcs      lines that open a function-like block of 2+ lines
    max_func   longest such block, in lines
    max_nest   deepest nesting inside one function, relative to its first line
    """
    rows, code = [], []
    for raw in text.splitlines():
        if not raw.strip() or COMMENT.match(raw):
            continue
        ws = raw[: len(raw) - len(raw.lstrip())]
        rows.append(ws.count("\t") * 4 + ws.count(" "))
        code.append(raw.strip())
    if not rows:
        return {"lines": 0, "indent": 0, "funcs": 0, "max_func": 0, "max_nest": 0}
    # indent unit: the most common positive step between consecutive lines
    steps = collections.Counter(b - a for a, b in zip(rows, rows[1:]) if 0 < b - a <= 8)
    unit = steps.most_common(1)[0][0] if steps else 4
    depth = [w // unit for w in rows]
    funcs = max_func = max_nest = 0
    for i, d in enumerate(depth):
        if not is_func_open(code[i]):
            continue
        j = i + 1
        while j < len(depth) and (depth[j] > d or (depth[j] == d and code[j].startswith(CONTINUES))):
            j += 1
        if j - i < 2:
            continue
        funcs += 1
        max_func = max(max_func, j - i)
        max_nest = max(max_nest, max(depth[i + 1:j]) - d)
    return {"lines": len(rows), "indent": sum(depth), "funcs": funcs,
            "max_func": max_func, "max_nest": max_nest}


def read_metrics(repo, path):
    try:
        with open(os.path.join(repo, path), encoding="utf-8", errors="replace") as f:
            return measure(f.read())
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--scope", default="", help="limit to this directory")
    ap.add_argument("--since", default="12 months", help='git --since value, e.g. "6 months"')
    ap.add_argument("--top", type=int, default=20, help="rows to print (0 = all)")
    ap.add_argument("--min-coupling", type=int, default=3)
    ap.add_argument("--coupling-top", type=int, default=15)
    ap.add_argument("--max-commit-files", type=int, default=40)
    ap.add_argument("--tests", action="store_true", help="also rank test files, separately")
    ap.add_argument("--exclude", nargs="*", default=[], help="globs to leave out")
    ap.add_argument("--measure", action="store_true",
                    help="print the complexity proxy for the given files and stop")
    ap.add_argument("paths", nargs="*", help="only these files")
    a = ap.parse_args()

    if a.measure:
        keys = ["lines", "indent", "funcs", "max_func", "max_nest"]
        print("path\t" + "\t".join(keys))
        for p in a.paths:
            m = read_metrics(".", p)
            print(p + "\t" + ("\t".join(str(m[k]) for k in keys) if m else "missing"))
        return

    repo = git(a.repo, "rev-parse", "--show-toplevel").strip()
    scope = a.scope.strip("/")
    pathspec = a.paths or [scope or "."]
    tracked = [p for p in git(repo, "ls-files", "--", *pathspec).splitlines()
               if is_source(p, a.exclude)]
    if not tracked:
        sys.exit("no tracked source files in scope")
    alive = set(tracked)

    log = git(repo, "log", "--no-merges", "-M", "--numstat", f"--since={a.since}",
              "--format=@@%H\x1f%an\x1f%s", "--", *pathspec)
    commits = collections.Counter()
    bugfix = collections.Counter()
    churned = collections.Counter()
    authors = collections.defaultdict(set)
    pairs = collections.Counter()
    renamed = {}  # older name -> current name; log is newest first
    n_commits, bulk = 0, 0
    cur = None

    def close(c):
        nonlocal bulk
        if c and 1 < len(c["files"]):
            if len(c["files"]) > a.max_commit_files:
                bulk += 1
                return
            fs = sorted(f for f in c["files"] if not is_test(f))
            for i, x in enumerate(fs):
                for y in fs[i + 1:]:
                    pairs[(x, y)] += 1

    for line in log.splitlines():
        if line.startswith("@@"):
            close(cur)
            _, author, subject = line[2:].split("\x1f", 2)
            cur = {"author": author, "fix": bool(BUGFIX.search(subject)), "files": set()}
            n_commits += 1
            continue
        parts = line.split("\t")
        if len(parts) != 3 or cur is None:
            continue
        new, old = rename_target(parts[2])
        path = renamed.get(new, new)
        if old:
            renamed[old] = path
        if path not in alive or path in cur["files"] or parts[:2] == ["0", "0"]:
            continue  # pure renames and mode changes are not churn
        cur["files"].add(path)
        commits[path] += 1
        authors[path].add(cur["author"])
        bugfix[path] += cur["fix"]
        if parts[0] != "-":
            churned[path] += int(parts[0]) + int(parts[1])
    close(cur)

    # history age is the whole repo's, not the window's
    roots = git(repo, "log", "--format=%at", "--max-parents=0").split()
    age_days = (time.time() - min(map(int, roots))) / 86400 if roots else 0
    young = age_days < YOUNG_DAYS or n_commits < YOUNG_COMMITS

    rows = []
    for p in tracked:
        m = read_metrics(repo, p)
        if m:
            rows.append(dict(path=p, commits=commits[p], bugfix=bugfix[p],
                             authors=len(authors[p]), churned=churned[p], **m))

    def ranked(group):
        if not group:
            return []
        mx = lambda k: max(r[k] for r in group) or 1
        mc, mi, mb = mx("commits"), mx("indent"), mx("bugfix")
        w = 0.5 if young else 1.0
        for r in group:
            r["score"] = (r["commits"] / mc) ** w * (r["indent"] / mi) * (1 + r["bugfix"] / mb)
        return sorted(group, key=lambda r: (-r["score"], -r["bugfix"], -r["commits"], r["path"]))

    cols = ["commits", "bugfix", "authors", "churned", "lines", "indent", "funcs", "max_func",
            "max_nest"]

    def table(title, group):
        out = ranked(group)
        print(f"# {title}: {len(out)} files")
        print("rank\tscore\tpath\t" + "\t".join(cols))
        for i, r in enumerate(out[: a.top or None], 1):
            print(f"{i}\t{r['score']:.3f}\t{r['path']}\t" + "\t".join(str(r[c]) for c in cols))

    print(f"# repo {repo} · scope {scope or '(all)'} · since {a.since} · "
          f"{n_commits} commits in window · history {age_days:.0f} days · "
          f"{len(rows)} source files")
    table("hotspots", [r for r in rows if not is_test(r["path"])])
    if a.tests:
        print()
        table("test hotspots", [r for r in rows if is_test(r["path"])])

    print(f"\n# coupling: pairs changed together in >= {a.min_coupling} commits "
          f"({bulk} bulk commits over {a.max_commit_files} files left out)")
    print("together\tshare\tfile_a\tfile_b")
    strong = [(n, x, y) for (x, y), n in pairs.items() if n >= a.min_coupling]
    strong.sort(key=lambda t: (-t[0], t[1], t[2]))
    for n, x, y in strong[: a.coupling_top]:
        share = n / max(1, min(commits[x], commits[y]))
        print(f"{n}\t{share:.0%}\t{x}\t{y}")
    if not strong:
        print("(none)")

    if young:
        print(f"\n# YOUNG HISTORY: {age_days:.0f} days, {n_commits} commits in the window "
              f"(thresholds {YOUNG_DAYS} days, {YOUNG_COMMITS} commits). Churn is mostly the "
              "initial build-out, so it was dampened (square root). Lean on indent, max_func, max_nest "
              "and bugfix when choosing.")
    if not any(commits.values()):
        print("\n# NO CHURN in the window: widen --since.")


if __name__ == "__main__":
    main()
