#!/usr/bin/env python3
"""Run a benchmark command repeatedly, and compare two results with perf-pass's keep rule.

Usage:
  bench.py run --cmd CMD --out FILE [--runs 10] [--warmup 2] [--cwd DIR] [--timeout 600] [--label L]
  bench.py ab  --cmd CMD --setup-a CMD --setup-b CMD --out-a FILE --out-b FILE [--runs 10] [--warmup 2] [--cwd DIR]
  bench.py compare BEFORE.json AFTER.json [--metric wall_ms] [--min-gain 5] [--higher-is-better] [--json]

run      Runs CMD --warmup times (discarded), then --runs times, recording wall time and
         peak RSS of each run. A stdout line "BENCH <name>=<number>" records an extra
         metric for that run (in-process ms, query count, ...). Every other stdout line
         is hashed, so the result shows whether all runs printed the same output.
ab       Alternates two versions, A then B, --runs rounds, running --setup-a or --setup-b
         (untimed) before each switch, so drift on the machine hits both alike. Ends with
         --setup-b, leaving the B version in place.
compare  Applies the keep rule: B beats A when its median is better by more than
         max(--min-gain %, 2 x A's relative spread). Spread is (p75 - p25) / median.
         A metric that is an identical integer in every run (a query count) is compared
         exactly. Also compares peak memory and the output hashes.

Standard library only. A failing run (non-zero exit or timeout) stops the script with exit code 1.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time

METRIC_LINE = re.compile(rb"^BENCH\s+([A-Za-z_][\w.-]*)=(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*$")


def run_once(cmd, cwd, timeout):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        start = time.perf_counter()
        proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=out, stderr=err,
                                start_new_session=True)
        killed = threading.Event()

        def kill():
            killed.set()
            os.killpg(proc.pid, signal.SIGKILL)  # the shell and everything it started

        timer = threading.Timer(timeout, kill)
        timer.start()
        try:
            _, status, usage = os.wait4(proc.pid, 0)
        finally:
            timer.cancel()
        wall_ms = (time.perf_counter() - start) * 1000
        proc.returncode = os.waitstatus_to_exitcode(status)
        out.seek(0)
        stdout = out.read()
        err.seek(0)
        stderr = err.read()

    if killed.is_set() or proc.returncode != 0:
        why = f"timed out after {timeout}s" if killed.is_set() else f"exit code {proc.returncode}"
        tail = stderr.decode(errors="replace").strip().splitlines()[-15:]
        sys.exit(f"bench.py: run failed ({why}): {cmd}\n" + "\n".join(tail))

    # ru_maxrss is bytes on macOS and kilobytes on Linux.
    rss_mb = usage.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    metrics = {"wall_ms": wall_ms, "peak_rss_mb": rss_mb}
    digest = hashlib.sha256()
    for line in stdout.splitlines():
        match = METRIC_LINE.match(line.strip())
        if match:
            metrics[match.group(1).decode()] = float(match.group(2))
        else:
            digest.update(line + b"\n")
    return metrics, digest.hexdigest()[:16]


def summarize(values):
    ordered = sorted(values)
    median = statistics.median(ordered)
    if len(ordered) > 1:
        p25, _, p75 = statistics.quantiles(ordered, n=4, method="inclusive")
    else:
        p25 = p75 = ordered[0]
    return {
        "median": median,
        "p25": p25,
        "p75": p75,
        "min": ordered[0],
        "max": ordered[-1],
        "rel_spread": (p75 - p25) / median if median else 0.0,
        "n": len(ordered),
    }


def environment():
    load = os.getloadavg() if hasattr(os, "getloadavg") else None
    return {
        "platform": platform.platform(),
        "cpus": os.cpu_count(),
        "load_avg_1m": round(load[0], 2) if load else None,
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
    }


class Recorder:
    def __init__(self, label, cmd, cwd, warmup):
        self.result = {"label": label, "cmd": cmd, "cwd": cwd, "warmup": warmup,
                       "env_start": environment(), "samples": {}, "hashes": []}

    def add(self, metrics, digest):
        for name, value in metrics.items():
            self.result["samples"].setdefault(name, []).append(value)
        self.result["hashes"].append(digest)

    def write(self, path):
        r = self.result
        r["env_end"] = environment()
        r["runs"] = len(r["hashes"])
        r["stats"] = {name: summarize(vals) for name, vals in r["samples"].items()}
        r["output_hashes"] = sorted(set(r["hashes"]))
        r["output_stable"] = len(r["output_hashes"]) == 1
        del r["hashes"]
        with open(path, "w") as fh:
            json.dump(r, fh, indent=2)
        wall = r["stats"]["wall_ms"]
        print(f"{r['label']}: {r['runs']} runs · wall median {wall['median']:.1f} ms "
              f"· spread {wall['rel_spread'] * 100:.1f}% · peak RSS "
              f"{r['stats']['peak_rss_mb']['median']:.1f} MB · output "
              f"{'stable' if r['output_stable'] else 'VARIES'} → {path}")


def cmd_run(args):
    for _ in range(args.warmup):
        run_once(args.cmd, args.cwd, args.timeout)
    rec = Recorder(args.label or os.path.basename(args.out), args.cmd, args.cwd, args.warmup)
    for _ in range(args.runs):
        rec.add(*run_once(args.cmd, args.cwd, args.timeout))
    rec.write(args.out)


def setup(cmd, cwd):
    done = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True)
    if done.returncode != 0:
        sys.exit(f"bench.py: setup failed (exit {done.returncode}): {cmd}\n"
                 + done.stderr.decode(errors="replace")[-2000:])


def cmd_ab(args):
    recs = {"a": Recorder("A", args.cmd, args.cwd, args.warmup),
            "b": Recorder("B", args.cmd, args.cwd, args.warmup)}
    setups = {"a": args.setup_a, "b": args.setup_b}
    for side in ("a", "b"):
        setup(setups[side], args.cwd)
        for _ in range(args.warmup):
            run_once(args.cmd, args.cwd, args.timeout)
    for _ in range(args.runs):
        for side in ("a", "b"):
            setup(setups[side], args.cwd)
            recs[side].add(*run_once(args.cmd, args.cwd, args.timeout))
    recs["a"].write(args.out_a)
    recs["b"].write(args.out_b)


def verdict(before, after, higher, min_gain):
    exact = (before["rel_spread"] == 0 and after["rel_spread"] == 0
             and before["min"] == before["max"] and after["min"] == after["max"]
             and float(before["median"]).is_integer() and float(after["median"]).is_integer())
    b, a = before["median"], after["median"]
    diff = (a - b) if higher else (b - a)
    gain = diff / b if b else 0.0
    if exact:
        threshold = 0.0
        word = "BETTER" if diff > 0 else "WORSE" if diff < 0 else "SAME"
    else:
        threshold = max(min_gain / 100, 2 * before["rel_spread"])
        if gain > threshold:
            word = "NEAR" if gain < 1.5 * threshold else "BETTER"
        elif gain < -threshold:
            word = "WORSE"
        else:
            word = "NO GAIN"
    return {"before": b, "after": a, "gain_pct": round(gain * 100, 2),
            "threshold_pct": round(threshold * 100, 2), "exact": exact, "verdict": word}


def cmd_compare(args):
    with open(args.before) as fh:
        before = json.load(fh)
    with open(args.after) as fh:
        after = json.load(fh)
    if args.metric not in before["stats"] or args.metric not in after["stats"]:
        sys.exit(f"bench.py: metric {args.metric!r} missing; have "
                 f"{sorted(before['stats'])} and {sorted(after['stats'])}")
    out = {"metric": args.metric,
           "primary": verdict(before["stats"][args.metric], after["stats"][args.metric],
                              args.higher_is_better, args.min_gain)}
    if args.metric != "peak_rss_mb":
        out["memory"] = verdict(before["stats"]["peak_rss_mb"], after["stats"]["peak_rss_mb"],
                                False, args.min_gain)
    if before["output_stable"] and after["output_stable"]:
        out["outputs"] = "same" if before["output_hashes"] == after["output_hashes"] else "DIFFERENT"
    else:
        out["outputs"] = "not comparable: output varies between runs"
    b_spread = before["stats"][args.metric]["rel_spread"]
    a_spread = after["stats"][args.metric]["rel_spread"]
    out["unstable"] = a_spread > 2 * max(b_spread, 0.01)
    out["load_avg_1m"] = [before["env_start"].get("load_avg_1m"), after["env_start"].get("load_avg_1m")]
    if args.json:
        print(json.dumps(out, indent=2))
        return
    p = out["primary"]
    print(f"{args.metric}: {p['before']:.4g} → {p['after']:.4g} · gain {p['gain_pct']}% "
          f"· threshold {p['threshold_pct']}% · {p['verdict']}")
    if "memory" in out:
        m = out["memory"]
        print(f"peak_rss_mb: {m['before']:.4g} → {m['after']:.4g} · {m['verdict']}")
    print(f"outputs: {out['outputs']}")
    if out["unstable"]:
        print(f"UNSTABLE: after spread {a_spread * 100:.1f}% vs before {b_spread * 100:.1f}%; re-run")
    print(f"load average (1m) at start: before {out['load_avg_1m'][0]} · after {out['load_avg_1m'][1]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--cmd", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--label")
    ab = sub.add_parser("ab")
    ab.add_argument("--cmd", required=True)
    ab.add_argument("--setup-a", required=True)
    ab.add_argument("--setup-b", required=True)
    ab.add_argument("--out-a", required=True)
    ab.add_argument("--out-b", required=True)
    for p in (run, ab):
        p.add_argument("--runs", type=int, default=10)
        p.add_argument("--warmup", type=int, default=2)
        p.add_argument("--cwd", default=None)
        p.add_argument("--timeout", type=float, default=600)

    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("before")
    cmp_.add_argument("after")
    cmp_.add_argument("--metric", default="wall_ms")
    cmp_.add_argument("--min-gain", type=float, default=5.0)
    cmp_.add_argument("--higher-is-better", action="store_true")
    cmp_.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if getattr(args, "runs", 1) < 1:
        sys.exit("bench.py: --runs must be at least 1")
    {"run": cmd_run, "ab": cmd_ab, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
