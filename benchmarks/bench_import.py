#!/usr/bin/env python3
"""Benchmark RichHandler import time before and after lazy Traceback import.

Usage:
    # From the repo root on the master branch:
    python benchmarks/bench_import.py

    # Or compare two branches (requires hyperfine):
    python benchmarks/bench_import.py --compare master perf/lazy-traceback-import

Requirements:
    pip install rich  (editable install: pip install -e .)
    Optional: hyperfine (https://github.com/sharkdp/hyperfine)
"""

import argparse
import shutil
import subprocess
import sys
import time


def measure_import(statement: str, runs: int = 50) -> tuple:
    """Measure import time using subprocess to get cold-start times."""
    times = []
    for _ in range(runs):
        start = time.perf_counter_ns()
        subprocess.run(
            [sys.executable, "-c", statement],
            capture_output=True,
        )
        elapsed = (time.perf_counter_ns() - start) / 1_000_000  # ms
        times.append(elapsed)

    times.sort()
    # Use median to reduce noise
    median = times[len(times) // 2]
    mean = sum(times) / len(times)
    stddev = (sum((t - mean) ** 2 for t in times) / len(times)) ** 0.5
    return median, mean, stddev


def run_basic_benchmark() -> None:
    """Run a simple before/after comparison using the current install."""
    print(f"Python: {sys.version}")
    print(f"Runs per measurement: 50\n")

    modules = [
        ("import rich", "rich (top-level)"),
        ("from rich.console import Console", "rich.console.Console"),
        ("from rich.logging import RichHandler", "rich.logging.RichHandler"),
        ("from rich.traceback import Traceback", "rich.traceback.Traceback"),
    ]

    print(f"{'Module':<30} {'Median (ms)':>12} {'Mean (ms)':>12} {'Stddev':>10}")
    print("-" * 66)
    for stmt, label in modules:
        median, mean, stddev = measure_import(stmt)
        print(f"{label:<30} {median:>12.1f} {mean:>12.1f} {stddev:>10.1f}")

    print()
    print("Key metric: the gap between Console and RichHandler reflects")
    print("the cost of the Traceback import chain (traceback -> syntax -> pygments).")
    print("With the lazy import, this gap should shrink from ~20ms to ~3ms.")


def run_hyperfine_compare(base: str, head: str) -> None:
    """Use hyperfine's --parameter-list to compare two branches in a single run.

    This uses hyperfine's native parameterization so both branches are measured
    in the same invocation, producing a proper relative comparison with
    statistical significance.
    """
    if not shutil.which("hyperfine"):
        print("Error: hyperfine not found. Install from https://github.com/sharkdp/hyperfine")
        sys.exit(1)

    branches = f"{base},{head}"
    print(f"Comparing {base} vs {head} using hyperfine\n")

    # RichHandler import (the key metric — includes traceback chain cost)
    print("=== RichHandler import ===\n")
    subprocess.run(
        [
            "hyperfine",
            "--warmup", "3",
            "--min-runs", "20",
            "-L", "branch", branches,
            "--setup", f"git checkout {{branch}} && {sys.executable} -m pip install -e . -q",
            "-n", "{branch}",
            f"{sys.executable} -c 'from rich.logging import RichHandler'",
        ],
        check=True,
    )

    # Console import (baseline — should be similar across branches)
    print("\n=== Console import (baseline) ===\n")
    subprocess.run(
        [
            "hyperfine",
            "--warmup", "3",
            "--min-runs", "20",
            "-L", "branch", branches,
            "--setup", f"git checkout {{branch}} && {sys.executable} -m pip install -e . -q",
            "-n", "{branch}",
            f"{sys.executable} -c 'from rich.console import Console'",
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RichHandler import time")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASE", "HEAD"),
        help="Compare two git branches using hyperfine",
    )
    args = parser.parse_args()

    if args.compare:
        run_hyperfine_compare(*args.compare)
    else:
        run_basic_benchmark()


if __name__ == "__main__":
    main()
