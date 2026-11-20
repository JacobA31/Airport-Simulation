"""Print an event trace of one replication, optionally with a per-passenger timeline.

Examples:
    python scripts/trace.py                                  # first 40 events of the baseline
    python scripts/trace.py --start 270 --until 400 --max-lines 100
    python scripts/trace.py --set operations.checkin_counters.coach=5
    python scripts/trace.py --until 31 --max-lines 60 --pax-table 10 --no-results   # verification trace (docs/verification.md)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airport_sim.config import load_config  # noqa: E402
from airport_sim.model import AirportModel  # noqa: E402
from airport_sim.rng import RandomStreams  # noqa: E402
from airport_sim.variates import Variates  # noqa: E402


def parse_overrides(pairs: list[str]) -> dict:
    out = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key] = yaml.safe_load(value)
    return out


def _f(x) -> str:
    return "-" if x is None else f"{x:.3f}"


def pax_table(passengers, n: int, ptype: str | None) -> list[str]:
    """Timeline of the first ``n`` passengers (of ``ptype``, if given), for hand checking.

    Columns: arrive, check-in queue join / start / end and service time S1,
    security queue join / start / end and service time S2, gate arrival, boarding.
    Hand checks: end = start + S; start >= join; wait = start - join.
    """
    head = (f"{'pax':>4} {'type':10} {'cabin':8} {'bags':>4} {'flight':>6} {'lead':>7} {'arrive':>9}"
            f" {'ci_start':>9} {'S1':>7} {'ci_end':>9} {'sc_start':>9} {'S2':>7} {'sc_end':>9}"
            f" {'board':>9}  status")
    lines = [head]
    rows = [p for p in passengers if ptype is None or p.ptype == ptype][:n]
    for p in rows:
        lines.append(
            f"{p.pid:>4} {p.ptype:10} {p.cabin:8} {p.bags:>4} {p.flight.fid if p.flight else '-':>6}"
            f" {_f(p.lead_time):>7} {_f(p.t_arrive):>9} {_f(p.t_s1):>9} {p.checkin_time:7.3f} {_f(p.t_e1):>9}"
            f" {_f(p.t_s2):>9} {p.security_time:7.3f} {_f(p.t_e2):>9} {_f(p.t_board):>9}  {p.status}"
            + (" (missed" + (", refunded)" if p.refunded else ")") if p.missed else ""))
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/baseline.yaml")
    ap.add_argument("--rep", type=int, default=0, help="replication number")
    ap.add_argument("--start", type=float, default=0.0, help="print events from this time (min)")
    ap.add_argument("--until", type=float, default=float("inf"), help="print events up to this time (min)")
    ap.add_argument("--max-lines", type=int, default=40)
    ap.add_argument("--pax-table", type=int, default=0, metavar="N",
                    help="after the run, print the timeline of the first N passengers")
    ap.add_argument("--pax-type", choices=("commuter", "provincial"),
                    help="show only events and timeline rows of this passenger type")
    ap.add_argument("--no-results", action="store_true", help="do not print the KPI dict")
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE", help="override config values")
    args = ap.parse_args()

    cfg = load_config(args.config, parse_overrides(args.set))
    printed = 0

    def other_type(line: str) -> bool:
        """True if the event line concerns only passengers/flights of the type not selected."""
        if args.pax_type is None:
            return False
        other = "commuter" if args.pax_type == "provincial" else "provincial"
        if f"{other.upper()}_DEPARTURE" in line:
            return True
        m = re.search(r"pax (\d+)", line)
        return m is not None and model.passengers[int(m.group(1)) - 1].ptype == other

    def trace(line: str) -> None:
        nonlocal printed
        t = float(line.split("t=")[1].split()[0])
        if args.start <= t <= args.until and printed < args.max_lines and not other_type(line):
            print(line)
            printed += 1

    variates = Variates(cfg["inputs"], RandomStreams(cfg["simulation"]["base_seed"], args.rep))
    model = AirportModel(cfg, variates, trace=trace)
    results = {"replication": args.rep, **model.run()}

    if args.pax_table:
        print("\n--- passenger timeline (times in minutes since d1 00:00) ---")
        print("\n".join(pax_table(model.passengers, args.pax_table, args.pax_type)))
    if not args.no_results:
        print("\n--- results ---")
        for key, value in results.items():
            print(f"{key:32s} {value}")


if __name__ == "__main__":
    main()
