#!/usr/bin/env python3
"""Rank a repository's tracked source files by how established they are.

Established = many authors, many commits, old, and still alive. These files
show the codebase's conventions; recently added files may not follow them yet.

Usage: established.py [--repo PATH] [--scope DIR] [--top N] [--recent-days D]
Prints a TSV of the top N files per top-level area, then the files added in the
last D days (for spotting conventions that are changing).
"""
import argparse
import collections
import math
import os
import subprocess
import sys
import time

SOURCE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java",
    ".kt", ".kts", ".scala", ".rb", ".php", ".cs", ".swift", ".m", ".c", ".h",
    ".cc", ".cpp", ".hpp", ".ex", ".exs", ".erl", ".clj", ".dart", ".lua",
    ".sql", ".sh", ".vue", ".svelte",
}
SKIP_PARTS = {
    "node_modules", "vendor", "third_party", "dist", "build", "out", "target",
    "generated", "gen", "__generated__", ".venv", "venv", "migrations",
}
SKIP_SUFFIXES = (".min.js", ".pb.go", "_pb2.py", ".g.dart", ".generated.ts", ".d.ts")


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, check=True
    ).stdout


def is_source(path):
    if path.endswith(SKIP_SUFFIXES):
        return False
    if set(path.split("/")[:-1]) & SKIP_PARTS:
        return False
    return os.path.splitext(path)[1] in SOURCE_EXT


def area(path, scope):
    rel = path[len(scope):].lstrip("/") if scope else path
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else "."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--scope", default="")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--recent-days", type=int, default=90)
    a = ap.parse_args()
    scope = a.scope.strip("/")

    tracked = [
        p for p in git(a.repo, "ls-files", "--", scope or ".").splitlines()
        if is_source(p)
    ]
    if not tracked:
        sys.exit("no tracked source files in scope")
    alive = set(tracked)

    commits = collections.Counter()
    authors = collections.defaultdict(set)
    first = {}
    log = git(a.repo, "log", "--no-merges", "--no-renames",
              "--format=@%an|%at", "--name-only", "--", scope or ".")
    author, ts = None, None
    for line in log.splitlines():
        if line.startswith("@"):
            author, t = line[1:].rsplit("|", 1)
            ts = int(t)
        elif line in alive:
            commits[line] += 1
            authors[line].add(author)
            first[line] = ts  # log is newest first, so the last seen is the oldest

    now = time.time()
    rows = []
    for p in tracked:
        age_years = (now - first.get(p, now)) / (365 * 86400)
        score = 2 * len(authors[p]) + math.log1p(commits[p]) + min(age_years, 5)
        rows.append((score, p, len(authors[p]), commits[p], age_years))

    by_area = collections.defaultdict(list)
    for r in sorted(rows, reverse=True):
        by_area[area(r[1], scope)].append(r)

    print("# established\tarea\tpath\tauthors\tcommits\tage_years")
    for ar in sorted(by_area):
        for score, p, au, c, age in by_area[ar][: a.top]:
            print(f"{score:.1f}\t{ar}\t{p}\t{au}\t{c}\t{age:.1f}")

    cutoff = a.recent_days / 365
    recent = sorted((r for r in rows if r[4] <= cutoff), key=lambda r: r[4])
    print(f"\n# added in the last {a.recent_days} days: {len(recent)} of {len(rows)} files"
          "\tpath\tauthors\tcommits")
    for _, p, au, c, _ in recent[:30]:
        print(f"recent\t{p}\t{au}\t{c}")

    all_authors = set().union(*authors.values()) if authors else set()
    if len(recent) > len(rows) / 2 or len(all_authors) < 2:
        print(f"\n# WEAK HISTORY: {len(all_authors)} author(s), {len(recent)} of {len(rows)} "
              "files are recent. History can't tell established code from new code; "
              "rely on prevalence and the user's confirmation.")


if __name__ == "__main__":
    main()
