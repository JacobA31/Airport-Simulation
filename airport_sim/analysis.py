"""Means, t-based confidence intervals, and replication-count planning.

Example:
    python -m airport_sim.analysis results/pilot.csv --target-rel 0.05
"""

from __future__ import annotations

import argparse
import math

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_KPIS = [
    "security_wait_mean_coach",   # KPI 1: mean security waiting time
    "prov_pct_missed",            # KPI 2: % of provincial passengers missing their flight
    "util_security_coach",        # KPI 3: utilization of security resources
    "profit",                     # KPI 4: total profit
]


def _t_crit(n: int, level: float) -> float:
    return float(stats.t.ppf(1 - (1 - level) / 2, n - 1))


def confidence_interval(x, level: float = 0.95) -> dict:
    """Mean +/- t_{n-1, 1-alpha/2} * s / sqrt(n) from independent replication results."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        raise ValueError("need at least 2 replications")
    mean, s = x.mean(), x.std(ddof=1)
    hw = _t_crit(n, level) * s / math.sqrt(n)
    return {"n": n, "mean": mean, "std": s, "half_width": hw,
            "ci_low": mean - hw, "ci_high": mean + hw}


def summarize(df: pd.DataFrame, kpis=DEFAULT_KPIS, level: float = 0.95) -> pd.DataFrame:
    """One row per KPI: n, mean, std, half_width, ci_low, ci_high."""
    return pd.DataFrame.from_dict({k: confidence_interval(df[k], level) for k in kpis},
                                  orient="index")


def replications_needed(x, half_width=None, rel_half_width=None,
                        level: float = 0.95, n_max: int = 100_000) -> int:
    """Smallest n >= len(pilot) with t_{n-1} * s / sqrt(n) <= target, using the pilot's s.

    Give exactly one target: an absolute half_width, or rel_half_width as a
    fraction of the pilot mean (e.g. 0.05 = 5%).
    """
    if (half_width is None) == (rel_half_width is None):
        raise ValueError("give exactly one of half_width or rel_half_width")
    x = np.asarray(x, dtype=float)
    s, mean = x.std(ddof=1), x.mean()
    target = half_width if half_width is not None else rel_half_width * abs(mean)
    for n in range(len(x), n_max):
        if _t_crit(n, level) * s / math.sqrt(n) <= target:
            return n
    raise RuntimeError("target not reached within n_max replications")


def paired_difference_ci(a, b, level: float = 0.95) -> dict:
    """CI for mean(b - a), pairing replication i of each system (same base_seed)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) != len(b):
        raise ValueError("paired comparison needs the same number of replications")
    return confidence_interval(b - a, level)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("csv", help="replication-level CSV from runner.py")
    ap.add_argument("--kpis", nargs="+", default=DEFAULT_KPIS)
    ap.add_argument("--level", type=float, default=0.95)
    ap.add_argument("--target-rel", type=float,
                    help="also report replications needed for this relative half-width")
    ap.add_argument("--out", help="save the summary table to this CSV")
    args = ap.parse_args(argv)

    df = pd.read_csv(args.csv)
    table = summarize(df, args.kpis, args.level)
    if args.target_rel is not None:
        table["n_needed"] = [replications_needed(df[k], rel_half_width=args.target_rel,
                                                 level=args.level) for k in table.index]
    print(table.to_string(float_format=lambda v: f"{v:,.4f}"))
    if args.out:
        table.to_csv(args.out)


if __name__ == "__main__":
    main()