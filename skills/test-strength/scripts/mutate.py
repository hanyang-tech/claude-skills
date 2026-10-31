#!/usr/bin/env python3
"""Run hand-made mutants one at a time in a scratch tree, restoring after each.

Each mutant is one JSON object per line in the mutants file:
  {"id": "M1", "file": "src/a.py", "line": 42, "end_line": 42,
   "find": "x < n", "replace": "x <= n", "op": "BND",
   "cmd": "python -m pytest -q tests/test_a.py", "build": null, "timeout": null}
- file is relative to --tree; line/end_line are 1-based and inclusive
  (end_line defaults to line). `find` must occur exactly once in those lines.
- cmd runs the covering tests from --tree. A null cmd means no test covers the
  line: the mutant is recorded "not covered" without running anything.
- build, if set, runs before cmd (compile or syntax check). A failing build
  makes the mutant "unviable" rather than killed.
- timeout defaults to max(--timeout-floor, --factor x the cmd's baseline time).

Usage:
  mutate.py check --tree DIR --mutants FILE
  mutate.py run --tree DIR --mutants FILE --out FILE [--budget MIN]
                [--factor 3] [--timeout-floor 10]
  mutate.py summary --mutants FILE --out FILE

`run` first runs every distinct cmd once on the unmutated tree; a cmd that
fails there marks its mutants "error: baseline fails". Results are appended to
--out as JSON lines, so a second `run` with the same --out resumes where the
budget or an interruption stopped it. Exit code 2 means a file could not be
restored, which needs a person to look at the tree.
"""
import argparse
import collections
import json
import os
import signal
import subprocess
import sys
import time

TAIL_LINES = 15


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def refuse_main_worktree(tree):
    """The tree must be a linked git worktree or not a git checkout at all."""
    def rev_parse(flag):
        r = subprocess.run(["git", "-C", tree, "rev-parse", flag],
                           capture_output=True, text=True)
        return os.path.realpath(os.path.join(tree, r.stdout.strip())) if r.returncode == 0 else None
    git_dir, common = rev_parse("--git-dir"), rev_parse("--git-common-dir")
    if git_dir and git_dir == common:
        sys.exit(f"refusing: {tree} is a repository's main working tree. "
                 "Mutate only in a scratch worktree or a copy.")


def apply(tree, m):
    """Return (path, original bytes, mutated text) or raise ValueError."""
    path = os.path.join(tree, m["file"])
    with open(path, "rb") as f:
        original = f.read()
    lines = original.decode("utf-8").splitlines(keepends=True)
    start, end = m["line"], m.get("end_line") or m["line"]
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"lines {start}-{end} outside file of {len(lines)} lines")
    block = "".join(lines[start - 1:end])
    if block.count(m["find"]) != 1:
        raise ValueError(f"find text occurs {block.count(m['find'])} times in lines {start}-{end}")
    mutated = "".join(lines[:start - 1]) + block.replace(m["find"], m["replace"]) + "".join(lines[end:])
    if mutated.encode("utf-8") == original:
        raise ValueError("mutation leaves the file unchanged")
    return path, original, mutated


def restore(path, original):
    with open(path, "wb") as f:
        f.write(original)
    with open(path, "rb") as f:
        if f.read() != original:
            print(f"RESTORE FAILED for {path}; stop and inspect the tree", file=sys.stderr)
            sys.exit(2)


def run_cmd(cmd, tree, timeout):
    """Run cmd in its own process group; return (exit code or None on timeout, seconds, tail)."""
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, shell=True, cwd=tree, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=timeout)
        code = p.returncode
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        code = None
    tail = "\n".join(out.decode("utf-8", "replace").splitlines()[-TAIL_LINES:])
    return code, round(time.monotonic() - t0, 2), tail


def check(a):
    bad = 0
    for m in load_jsonl(a.mutants):
        try:
            apply(a.tree, m)
        except (ValueError, OSError) as e:
            bad += 1
            print(f"{m['id']}\t{m['file']}:{m['line']}\t{e}")
    print(f"{bad} mutant(s) do not apply" if bad else "all mutants apply")
    return 1 if bad else 0


def run(a):
    tree = os.path.realpath(a.tree)
    refuse_main_worktree(tree)
    mutants = load_jsonl(a.mutants)
    previous = load_jsonl(a.out)
    done = {r["id"] for r in previous if r.get("type") == "mutant"}
    baseline = {r["cmd"]: r for r in previous if r.get("type") == "baseline"}
    deadline = time.monotonic() + a.budget * 60
    out = open(a.out, "a", encoding="utf-8")

    def write(rec):
        out.write(json.dumps(rec) + "\n")
        out.flush()

    for cmd in dict.fromkeys(m["cmd"] for m in mutants if m.get("cmd")):
        if cmd not in baseline:
            code, secs, tail = run_cmd(cmd, tree, None)
            baseline[cmd] = {"type": "baseline", "cmd": cmd, "exit": code, "seconds": secs, "tail": tail}
            write(baseline[cmd])
            print(f"baseline {'ok' if code == 0 else 'FAILS'} {secs}s  {cmd}")

    counts = collections.Counter()
    for m in mutants:
        if m["id"] in done:
            continue
        if time.monotonic() > deadline:
            print("budget spent; run again with the same --out to resume")
            break
        rec = {"type": "mutant", "id": m["id"], "file": m["file"], "line": m["line"], "op": m.get("op")}
        try:
            path, original, mutated = apply(tree, m)
        except (ValueError, OSError) as e:
            rec.update(status="error", detail=str(e))
            write(rec)
            counts["error"] += 1
            continue
        if not m.get("cmd"):
            rec["status"] = "not covered"
        elif baseline[m["cmd"]]["exit"] != 0:
            rec.update(status="error", detail="baseline fails for this cmd")
        else:
            timeout = m.get("timeout") or max(a.timeout_floor, a.factor * baseline[m["cmd"]]["seconds"])
            try:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(mutated)
                status = None
                if m.get("build"):
                    code, secs, tail = run_cmd(m["build"], tree, timeout)
                    if code != 0:
                        status = "unviable"
                        rec.update(seconds=secs, tail=tail)
                if status is None:
                    code, secs, tail = run_cmd(m["cmd"], tree, timeout)
                    status = "timeout" if code is None else "survived" if code == 0 else "killed"
                    rec.update(seconds=secs, tail=tail, timeout=timeout)
                rec["status"] = status
            finally:
                restore(path, original)
        write(rec)
        counts[rec["status"]] += 1
        print(f"{m['id']}\t{rec['status']}\t{m['file']}:{m['line']}")
    out.close()
    print("this run: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "nothing to do"))
    return 0


def summary(a):
    mutants = load_jsonl(a.mutants)
    results = {r["id"]: r for r in load_jsonl(a.out) if r.get("type") == "mutant"}
    cols = ["killed", "timeout", "survived", "not covered", "unviable", "error", "not run"]
    per_file = collections.defaultdict(collections.Counter)
    for m in mutants:
        per_file[m["file"]][results.get(m["id"], {}).get("status", "not run")] += 1
    print("| File | Mutants | " + " | ".join(c.capitalize() for c in cols) + " | Score |")
    print("|---" * (len(cols) + 3) + "|")
    total = collections.Counter()
    for f in sorted(per_file):
        total.update(per_file[f])
        print(row(f, per_file[f], cols))
    print(row("**Total**", total, cols))
    print("\nScore = (killed + timeout) / (killed + timeout + survived + not covered). "
          "Equivalent mutants are taken out in Step 4; unviable, error and not run never count.")
    return 0


def row(name, c, cols):
    scored = c["killed"] + c["timeout"] + c["survived"] + c["not covered"]
    score = f"{100 * (c['killed'] + c['timeout']) / scored:.0f}%" if scored else "–"
    return f"| {name} | {sum(c.values())} | " + " | ".join(str(c[k]) for k in cols) + f" | {score} |"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check")
    p.add_argument("--tree", required=True)
    p.add_argument("--mutants", required=True)
    p = sub.add_parser("run")
    p.add_argument("--tree", required=True)
    p.add_argument("--mutants", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--budget", type=float, default=20, help="minutes")
    p.add_argument("--factor", type=float, default=3)
    p.add_argument("--timeout-floor", type=float, default=10, help="seconds")
    p = sub.add_parser("summary")
    p.add_argument("--mutants", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"check": check, "run": run, "summary": summary}[a.command](a)


if __name__ == "__main__":
    sys.exit(main())
