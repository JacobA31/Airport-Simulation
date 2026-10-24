"""Run one replication and print its KPI dict.

Examples:
    python scripts/run_once.py
    python scripts/run_once.py --rep 3 --set operations.checkin_counters.coach=5
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airport_sim.config import load_config  # noqa: E402
from airport_sim.model import run_replication  # noqa: E402
from scripts.trace import parse_overrides  # noqa: E402


def fmt(value) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return "nan" if math.isnan(value) else f"{value:,.3f}"
    return f"{value:,}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/baseline.yaml")
    ap.add_argument("--rep", type=int, default=0, help="replication number")
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="override config values")
    args = ap.parse_args()

    cfg = load_config(args.config, parse_overrides(args.set))
    t0 = time.perf_counter()
    results = run_replication(cfg, args.rep)
    elapsed = time.perf_counter() - t0
    for key, value in results.items():
        print(f"{key:30s} {fmt(value):>16s}")
    print(f"\n(run time {elapsed:.2f} s)")


if __name__ == "__main__":
    main()
