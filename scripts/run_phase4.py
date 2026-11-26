"""Run Person A's Phase IV experiments with N replications each (report §10, §12).

Experiments (DECISIONS.md D4, D26):
  * the three security-lane alternatives and the 1+4 side check;
  * the D4 robustness check: baseline and the three alternatives at
    other_delay_prob = 0.05 and 0.2 (the baseline value is 0.1).

The baseline itself (results/baseline.csv) is run by the replication runner as
step 2 of "Reproducing the reported experiments" in the README. Pass
--with-baseline to run it here as well.

Every run goes through airport_sim.runner, so each CSV gets its .config.yaml
record, and all runs use the same base_seed (common random numbers).

Example (from the project root):
    python scripts/run_phase4.py --reps N
    python scripts/compare_alternatives.py
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from airport_sim import runner  # noqa: E402

ALTERNATIVES = ["a1_share", "a2_coach3", "a3_coach3_share", "check_coach4"]
ROBUSTNESS_CONFIGS = ["baseline", "a1_share", "a2_coach3", "a3_coach3_share"]
ROBUSTNESS_P = [0.05, 0.2]                      # baseline other_delay_prob is 0.1 (D4)
P_KEY = "inputs.checkin.other_delay_prob"


def config_path(name: str) -> str:
    return "config/baseline.yaml" if name == "baseline" else f"config/alternatives/{name}.yaml"


def p_tag(p: float) -> str:
    return f"p{p:g}".replace(".", "")            # 0.05 -> p005, 0.2 -> p02


def planned_runs(out_dir: pathlib.Path, with_baseline: bool) -> list[tuple[str, list[str]]]:
    runs = []
    if with_baseline:
        runs.append(("baseline", ["--config", config_path("baseline"), "--out", str(out_dir / "baseline.csv")]))
    for name in ALTERNATIVES:
        runs.append((name, ["--config", config_path(name), "--out", str(out_dir / f"{name}.csv")]))
    for p in ROBUSTNESS_P:
        for name in ROBUSTNESS_CONFIGS:
            out = out_dir / f"robust_{p_tag(p)}_{name}.csv"
            runs.append((f"{name} at p={p:g}", ["--config", config_path(name), "--set", f"{P_KEY}={p}",
                                                "--out", str(out)]))
    return runs


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--reps", type=int, required=True, help="replications per experiment (the final N)")
    ap.add_argument("--out-dir", default="results", help="directory for the CSVs (default: results)")
    ap.add_argument("--with-baseline", action="store_true", help="also run the baseline")
    args = ap.parse_args(argv)

    out_dir = pathlib.Path(args.out_dir)
    for label, run_args in planned_runs(out_dir, args.with_baseline):
        print(f"{label}: ", end="", flush=True)
        runner.main([*run_args, "--reps", str(args.reps)])


if __name__ == "__main__":
    main()
