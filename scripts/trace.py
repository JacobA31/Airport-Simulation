"""Print an event trace of one replication.

Examples:
    python scripts/trace.py                                  # first 40 events of the baseline
    python scripts/trace.py --start 270 --until 400 --max-lines 100
    python scripts/trace.py --set operations.checkin_counters.coach=5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airport_sim.config import load_config  # noqa: E402
from airport_sim.model import run_replication  # noqa: E402


def parse_overrides(pairs: list[str]) -> dict:
    out = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key] = yaml.safe_load(value)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/baseline.yaml")
    ap.add_argument("--rep", type=int, default=0, help="replication number")
    ap.add_argument("--start", type=float, default=0.0, help="print events from this time (min)")
    ap.add_argument("--until", type=float, default=float("inf"), help="print events up to this time (min)")
    ap.add_argument("--max-lines", type=int, default=40)
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="override config values")
    args = ap.parse_args()

    cfg = load_config(args.config, parse_overrides(args.set))
    printed = 0

    def trace(line: str) -> None:
        nonlocal printed
        t = float(line.split("t=")[1].split()[0])
        if args.start <= t <= args.until and printed < args.max_lines:
            print(line)
            printed += 1

    results = run_replication(cfg, args.rep, trace=trace)
    print("\n--- results ---")
    for key, value in results.items():
        print(f"{key:32s} {value}")


if __name__ == "__main__":
    main()
