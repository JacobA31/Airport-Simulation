"""Check the passenger-conservation identities on every row of replication CSVs.

Examples:
    python scripts/check_conservation.py results/pilot.csv
    python scripts/check_conservation.py results/*.csv

Exit status is 1 if any row breaks an identity. Files without the model's
end-of-run columns (e.g. output of the development stub) are reported and skipped.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from airport_sim.checks import conservation_violations  # noqa: E402
from airport_sim.config import load_config  # noqa: E402

REQUIRED = ("comm_arrived", "pax_in_system_end", "end_gate_commuters", "checkin_completed")


def _num(value: str):
    try:
        return float(value)
    except ValueError:
        return value                       # e.g. staffing_ok = "True"


def all_use_checkin(csv_path: Path) -> bool:
    """Read the run record written next to the CSV to see whether the D5 skip flag was on."""
    record = csv_path.with_suffix(".config.yaml")
    if not record.exists():
        return True
    rec = yaml.safe_load(record.read_text()) or {}
    if "config_file" not in rec:
        return True
    cfg = load_config(rec["config_file"], rec.get("overrides") or {})
    return not cfg["operations"]["commuter_zero_bag_skips_checkin"]


def check_file(path: Path) -> tuple[int, int] | None:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or not all(c in rows[0] for c in REQUIRED):
        print(f"{path}: not model output (missing end-of-run columns), skipped")
        return None
    flag = all_use_checkin(path)
    n_bad = 0
    for row in rows:
        bad = conservation_violations({k: _num(v) for k, v in row.items()}, all_use_checkin=flag)
        if bad:
            n_bad += 1
            print(f"{path} replication {row.get('replication')}: " + "; ".join(bad))
    print(f"{path}: {len(rows) - n_bad}/{len(rows)} replications satisfy every identity")
    return len(rows), n_bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+", type=Path)
    args = ap.parse_args()
    results = [r for r in (check_file(p) for p in args.csv) if r is not None]
    sys.exit(1 if any(n_bad for _, n_bad in results) else 0)


if __name__ == "__main__":
    main()
