#!/usr/bin/env python3
"""Build a repository's internal import graph and report cycles and layering violations.

For Python and JS/TS, when no boundary tool (import-linter, dependency-cruiser, madge)
is installed. Reads files only; runs no project code. Standard library only.

  python3 import_graph.py --repo <path> [--scope <dir>] [--collapse N|dir]
      [--include lazy,type] [--layers top,...,bottom] [--forbid from=to ...]
      [--edges <file.tsv>]

Edges are classified as runtime (module level), lazy (inside a function, or a dynamic
import()) and type (under TYPE_CHECKING, or `import type`). Cycles use runtime edges
unless --include adds the others. Only edges between the repository's own files count.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque

PY_EXT = (".py",)
JS_EXT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte")
SKIP_DIRS = {"node_modules", "dist", "build", "out", "vendor", ".venv", "venv", "site-packages",
             "__pycache__", ".next", ".nuxt", "coverage", "target", ".git"}
PY_ROOT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg")


def list_files(repo, scope):
    out = subprocess.run(["git", "-C", repo, "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    files = []
    for f in out:
        parts = f.split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        if os.path.isfile(os.path.join(repo, f)):
            files.append(f)
    in_scope = [f for f in files if not scope or f == scope or f.startswith(scope.rstrip("/") + "/")]
    return files, in_scope


def under(path, prefix):
    prefix = prefix.strip("/")
    return prefix in ("", ".") or path == prefix or path.startswith(prefix + "/")


# ---------- Python ----------

def py_modules(files):
    """Name each module twice over: from its package structure (walking up while the
    directory has __init__.py) and from the nearest project root (pyproject, setup, src/),
    which covers namespace packages. Relative imports use the longer name."""
    fileset = set(files)
    roots = {""}
    for f in files:
        d, base = os.path.split(f)
        if base in PY_ROOT_MARKERS:
            roots.add(d)
            roots.add(os.path.join(d, "src") if d else "src")
    modules = defaultdict(list)  # dotted name -> [(file, root, loose)]
    file_mod = {}
    for f in files:
        if not f.endswith(".py"):
            continue
        d = os.path.dirname(f)
        while d and os.path.join(d, "__init__.py") in fileset:
            d = os.path.dirname(d)
        names = []
        # A module outside any package is importable only from its own directory tree.
        loose_pkg = d == os.path.dirname(f) and not f.endswith("__init__.py")
        for root, loose in ((d, loose_pkg), (max((r for r in roots if under(f, r)), key=len), False)):
            rel = f[len(root) + 1:] if root else f
            parts = rel[:-3].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts and all(p.isidentifier() for p in parts):
                names.append((".".join(parts), root, loose))
        seen = set()
        for name, root, loose in names:
            if name not in seen:
                seen.add(name)
                modules[name].append((f, root, loose))
        names = [n for n, _, _ in names]
        if names:
            file_mod[f] = max(names, key=lambda n: n.count("."))
    return modules, file_mod


def py_kind(node, parents):
    p = parents.get(node)
    while p is not None:
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return "lazy"
        if isinstance(p, ast.If):
            t = ast.unparse(p.test)
            if "TYPE_CHECKING" in t:
                return "type"
        p = parents.get(p)
    return "runtime"


def py_edges(repo, files, all_files, problems):
    modules, file_mod = py_modules(all_files)
    in_scope = set(files)

    stdlib = getattr(sys, "stdlib_module_names", set())

    def lookup(name, importer):
        while name:
            cands = [(f, r) for f, r, loose in modules.get(name, ())
                     if not loose or under(importer, r)]
            if name.partition(".")[0] in stdlib:
                cands = [(f, r) for f, r in cands if r and under(importer, r)]
            if cands:
                near = [c for c in cands if c[1] and under(importer, c[1])]
                return (near or cands)[0][0]
            name = name.rpartition(".")[0]
        return None

    edges = []
    parsed = 0
    for f, mod in file_mod.items():
        if f not in in_scope:
            continue
        parsed += 1
        try:
            src = open(os.path.join(repo, f), encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except (SyntaxError, ValueError) as e:
            problems.append(f"{f}: {e.__class__.__name__}")
            continue
        parents = {}
        for p in ast.walk(tree):
            for c in ast.iter_child_nodes(p):
                parents[c] = p
        is_pkg = f.endswith("__init__.py")
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = mod.split(".") if is_pkg else mod.split(".")[:-1]
                    up = node.level - 1
                    if up > len(base_parts):
                        problems.append(f"{f}:{node.lineno}: relative import beyond top level")
                        continue
                    base_parts = base_parts[:len(base_parts) - up]
                    base = ".".join(base_parts + ([node.module] if node.module else []))
                else:
                    base = node.module or ""
                for a in node.names:
                    full = f"{base}.{a.name}" if base else a.name
                    targets.append(full if full in modules else base)
            else:
                continue
            kind = py_kind(node, parents)
            for t in targets:
                dst = lookup(t, f) if t else None
                if dst and dst != f:
                    edges.append((f, dst, node.lineno, kind))
    return list(dict.fromkeys(edges)), parsed


# ---------- JS / TS ----------

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"(^|[^:\\'\"])//[^\n]*")
FROM_RE = re.compile(r"\b(import|export)\s+(type\s+)?(?:(?!\b(?:import|export)\b)[^'\";])*?\bfrom\s*['\"]([^'\"]+)['\"]", re.S)
SIDE_RE = re.compile(r"\bimport\s*['\"]([^'\"]+)['\"]")
REQ_RE = re.compile(r"\brequire\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
DYN_RE = re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")


def strip_comments(text):
    text = BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return LINE_COMMENT.sub(lambda m: m.group(1), text)


def load_jsonc(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    text = strip_comments(text)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def js_aliases(repo, files, problems):
    aliases = []  # (tsconfig dir, prefix, suffix, [target patterns relative to repo])
    for f in files:
        if not re.search(r"(^|/)(ts|js)config[^/]*\.json$", f):
            continue
        try:
            opts = load_jsonc(os.path.join(repo, f)).get("compilerOptions", {}) or {}
        except (ValueError, OSError) as e:
            problems.append(f"{f}: unreadable ({e.__class__.__name__})")
            continue
        d = os.path.dirname(f)
        base = os.path.normpath(os.path.join(d, opts.get("baseUrl", ".")))
        for pat, targets in (opts.get("paths") or {}).items():
            pre, _, suf = pat.partition("*")
            aliases.append((d, pre, suf if "*" in pat else None,
                            [os.path.normpath(os.path.join(base, t)) for t in targets]))
    aliases.sort(key=lambda a: -len(a[0]))
    return aliases


def js_workspaces(repo, files):
    pkgs = {}
    for f in files:
        if os.path.basename(f) == "package.json" and f != "package.json":
            try:
                data = json.load(open(os.path.join(repo, f), encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if isinstance(data.get("name"), str):
                pkgs[data["name"]] = (os.path.dirname(f), data)
    return pkgs


def js_resolve_file(p, fileset):
    p = os.path.normpath(p)
    cands = [p] + [p + e for e in JS_EXT] + [os.path.join(p, "index" + e) for e in JS_EXT]
    stem, ext = os.path.splitext(p)
    swap = {".js": [".ts", ".tsx"], ".jsx": [".tsx"], ".mjs": [".mts"], ".cjs": [".cts"]}
    cands += [stem + e for e in swap.get(ext, [])]
    for c in cands:
        if c in fileset:
            return c
    return None


def js_edges(repo, files, all_files, problems):
    fileset = set(all_files)
    aliases = js_aliases(repo, all_files, problems)
    workspaces = js_workspaces(repo, all_files)
    js_files = [f for f in files if f.endswith(JS_EXT)]

    def resolve(spec, importer):
        if spec.startswith("."):
            return js_resolve_file(os.path.join(os.path.dirname(importer), spec), fileset), True
        for d, pre, suf, targets in aliases:
            if not under(importer, d):
                continue
            if suf is None and spec == pre:
                star = ""
            elif suf is not None and spec.startswith(pre) and spec.endswith(suf) and len(spec) >= len(pre) + len(suf):
                star = spec[len(pre):len(spec) - len(suf)] if suf else spec[len(pre):]
            else:
                continue
            for t in targets:
                r = js_resolve_file(t.replace("*", star), fileset)
                if r:
                    return r, True
            return None, True
        for name, (d, data) in workspaces.items():
            if spec == name or spec.startswith(name + "/"):
                sub = spec[len(name):].lstrip("/")
                tries = [sub] if sub else [data.get(k) for k in ("source", "main", "module", "types")
                                           if isinstance(data.get(k), str)] + ["src/index", "index"]
                for t in tries:
                    for v in (t, t.replace("dist/", "src/", 1), t.replace("lib/", "src/", 1)):
                        r = js_resolve_file(os.path.join(d, v), fileset)
                        if r:
                            return r, True
                return os.path.join(d, "package.json"), True
        return None, False

    edges = []
    for f in js_files:
        try:
            text = strip_comments(open(os.path.join(repo, f), encoding="utf-8", errors="replace").read())
        except OSError as e:
            problems.append(f"{f}: {e}")
            continue
        found = [(m.start(), m.group(3), "type" if m.group(2) else "runtime") for m in FROM_RE.finditer(text)]
        found += [(m.start(), m.group(1), "runtime") for m in SIDE_RE.finditer(text)]
        found += [(m.start(), m.group(1), "runtime") for m in REQ_RE.finditer(text)]
        found += [(m.start(), m.group(1), "lazy") for m in DYN_RE.finditer(text)]
        for pos, spec, kind in found:
            line = text.count("\n", 0, pos) + 1
            dst, internal = resolve(spec, f)
            if dst and dst != f:
                edges.append((f, dst, line, kind))
            elif internal and not dst:
                problems.append(f"{f}:{line}: unresolved internal import '{spec}'")
    return list(dict.fromkeys(edges)), len(js_files)


# ---------- graph ----------

def node_of(path, collapse):
    if collapse == "dir":
        return os.path.dirname(path) or "."
    if collapse:
        parts = path.split("/")[:-1]
        return "/".join(parts[:collapse]) or "."
    return path


def sccs(graph):
    index, low, stack, on, out, counter = {}, {}, [], set(), [], [0]
    for start in sorted(graph):
        if start in index:
            continue
        work = [(start, iter(sorted(graph[start])))]
        index[start] = low[start] = counter[0]; counter[0] += 1
        stack.append(start); on.add(start)
        while work:
            v, it = work[-1]
            nxt = next(it, None)
            if nxt is not None:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]; counter[0] += 1
                    stack.append(nxt); on.add(nxt)
                    work.append((nxt, iter(sorted(graph.get(nxt, ())))))
                elif nxt in on:
                    low[v] = min(low[v], index[nxt])
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop(); on.discard(w); comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    out.append(sorted(comp))
    return sorted(out, key=lambda c: (-len(c), c))


def shortest_cycle(comp, graph):
    members, start = set(comp), comp[0]
    prev, q = {start: None}, deque([start])
    while q:
        v = q.popleft()
        for w in sorted(graph.get(v, ())):
            if w == start:
                path = [v]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                return list(reversed(path)) + [start]
            if w in members and w not in prev:
                prev[w] = v
                q.append(w)
    return comp + [start]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--scope", default="")
    ap.add_argument("--collapse", default="0", help="0 = per file (default), N = first N directories, dir = parent directory")
    ap.add_argument("--include", default="", help="also count lazy and/or type edges in cycles, e.g. lazy,type")
    ap.add_argument("--layers", default="", help="path prefixes, top layer first; a lower layer may not import a higher one")
    ap.add_argument("--forbid", action="append", default=[], help="from_prefix=to_prefix, repeatable")
    ap.add_argument("--edges", help="write every edge as TSV to this file")
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    collapse = "dir" if a.collapse == "dir" else int(a.collapse)
    kinds = {"runtime"} | {k for k in a.include.split(",") if k}
    all_files, files = list_files(repo, a.scope)
    problems = []
    py, n_py = py_edges(repo, files, all_files, problems)
    js, n_js = js_edges(repo, files, all_files, problems)
    edges = py + js

    graph, example = defaultdict(set), {}
    for src, dst, line, kind in edges:
        if kind not in kinds:
            continue
        u, v = node_of(src, collapse), node_of(dst, collapse)
        if u == v:
            continue
        graph[u].add(v)
        example.setdefault((u, v), f"{src}:{line}")

    counts = {k: sum(1 for e in edges if e[3] == k) for k in ("runtime", "lazy", "type")}
    print(f"IMPORT GRAPH repo={repo} scope={a.scope or '.'} collapse={a.collapse} cycles-use={','.join(sorted(kinds))}")
    print(f"Files: python {n_py} · js/ts {n_js}")
    print(f"Edges: {len(edges)} (runtime {counts['runtime']}, lazy {counts['lazy']}, type {counts['type']})"
          f" · nodes in counted graph {len(set(graph) | {v for s in graph.values() for v in s})}")

    comps = sccs(graph)
    print(f"\nCYCLES: {len(comps)} strongly connected groups" + (f" (sizes {', '.join(str(len(c)) for c in comps)})" if comps else ""))
    for i, comp in enumerate(comps, 1):
        cyc = shortest_cycle(comp, graph)
        shown = ", ".join(comp[:12]) + (f", … {len(comp) - 12} more" if len(comp) > 12 else "")
        print(f"## SCC {i} — {len(comp)} nodes: {shown}")
        chain = cyc[0] + "".join(f" -> {b} ({example[(x, b)]})" for x, b in zip(cyc, cyc[1:]))
        print(f"  shortest cycle: {chain}")

    rules = [tuple(r.split("=", 1)) for r in a.forbid if "=" in r]
    layers = [l.strip() for l in a.layers.split(",") if l.strip()]
    viol = []
    for src, dst, line, kind in edges:
        for fr, to in rules:
            if under(src, fr) and under(dst, to) and not under(src, to):
                viol.append(f"{src}:{line}  {fr} -> {to}  imports {dst} [{kind}]  rule: forbid {fr}={to}")
        if layers:
            ls = next((i for i, l in enumerate(layers) if under(src, l)), None)
            ld = next((i for i, l in enumerate(layers) if under(dst, l)), None)
            if ls is not None and ld is not None and ld < ls:
                viol.append(f"{src}:{line}  {layers[ls]} -> {layers[ld]}  imports {dst} [{kind}]  rule: layers")
    if rules or layers:
        print(f"\nVIOLATIONS: {len(viol)}")
        for v in viol:
            print("  " + v)

    print(f"\nPROBLEMS: {len(problems)}" + (" (first 20)" if len(problems) > 20 else ""))
    for p in problems[:20]:
        print("  " + p)

    if a.edges:
        with open(a.edges, "w", encoding="utf-8") as fh:
            fh.write("from\tto\tline\tkind\n")
            for e in edges:
                fh.write("\t".join(map(str, e)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
