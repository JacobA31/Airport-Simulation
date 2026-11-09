"""Run N independent replications of one experiment and save replication-level output.

Example (from the project root):
    python -m airport_sim.runner --reps 10 --out results/pilot.csv
    python -m airport_sim.runner --reps 30 --set operations.checkin_counters.coach=4 --out results/alt_a.csv
"""

from __future__ import annotations

import argparse
import csv
import pathlib

import yaml

from airport_sim.config import load_config
from airport_sim.model import run_replication

# Where these two settings live in config/baseline.yaml. EDIT to match your file.
REPS_KEY = "simulation.replications"
SEED_KEY = "simulation.base_seed"


def get_path(cfg: dict, dotted_key: str):
    """cfg['a']['b'] for 'a.b'. Assumes load_config returns nested dicts."""
    node = cfg
    for k in dotted_key.split("."):
        node = node[k]
    return node


def parse_overrides(items: list[str]) -> dict:
    """['a.b=3', 'c.d=[1,2]'] -> {'a.b': 3, 'c.d': [1, 2]} (values parsed as YAML)."""
    overrides = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"--set expects KEY=VALUE, got {item!r}")
        overrides[key] = yaml.safe_load(value)
    return overrides


def run_experiment(cfg: dict, n_reps: int) -> list[dict]:
    base_seed = get_path(cfg, SEED_KEY)
    rows = []
    for r in range(n_reps):
        row = run_replication(cfg, replication=r)          # model builds its own streams
        rows.append({"base_seed": base_seed, "replication": r, **row})
    return rows


def write_csv(rows: list[dict], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="config/baseline.yaml")
    ap.add_argument("--out", required=True, help="replication-level CSV to write")
    ap.add_argument("--reps", type=int, help=f"number of replications (default: {REPS_KEY})")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a config value, e.g. operations.checkin_counters.coach=4")
    args = ap.parse_args(argv)

    overrides = parse_overrides(args.set)
    cfg = load_config(args.config, overrides)
    n_reps = args.reps if args.reps is not None else get_path(cfg, REPS_KEY)

    rows = run_experiment(cfg, n_reps)

    out = pathlib.Path(args.out)
    write_csv(rows, out)
    # Record how this run was produced (config file + overrides), for reproducibility.
    with open(out.with_suffix(".config.yaml"), "w") as f:
        yaml.safe_dump({"config_file": args.config, "overrides": overrides,
                        "replications": n_reps}, f, sort_keys=False)
    print(f"{len(rows)} replications -> {out}")


if __name__ == "__main__":
    main()