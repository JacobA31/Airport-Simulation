"""Comparison tables for the security-lane alternatives (report §10 and §12).

Reads the replication-level CSVs written by scripts/run_phase4.py (and
results/baseline.csv) and writes one Markdown file with:

  10.1  principal KPIs per configuration (mean ± 95% half-width)
  10.2  secondary measures per configuration
  10.3  paired differences, alternative − baseline
  10.4  2 × 2 effects: adding a lane, turning sharing on, and the 1+4 side check
  12.1  break-even security wage for each extra lane (D27)
  12.2  robustness to the D4 assumption (other_delay_prob 0.05 / 0.1 / 0.2)

Differences are paired by replication: every configuration uses the same
base_seed, so replication r sees the same passengers in each (common random
numbers). A difference is marked * when its 95% CI excludes zero.

Example (from the project root):
    python scripts/compare_alternatives.py                       # -> results/phase4_tables.md
    python scripts/compare_alternatives.py --results-dir other/ --out other/tables.md
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from airport_sim.analysis import confidence_interval, paired_difference_ci  # noqa: E402
from airport_sim.config import load_config  # noqa: E402

CONFIGS = {  # file stem -> (label, business lanes, coach lanes, sharing)
    "baseline": ("Baseline", 1, 2, "off"),
    "a1_share": ("A1", 1, 2, "on"),
    "a2_coach3": ("A2", 1, 3, "off"),
    "a3_coach3_share": ("A3", 1, 3, "on"),
    "check_coach4": ("Check", 1, 4, "off"),
}
PRINCIPAL = {
    "security_wait_mean_coach": "Coach security wait (min)",
    "prov_pct_missed": "Provincial missed (%)",
    "util_security_coach": "Coach security utilization",
    "profit": "Profit ($)",
}
SECONDARY = {
    "security_wait_mean_business": "Business security wait (min)",
    "util_security_business": "Business lane utilization",
    "checkin_wait_mean_coach": "Coach check-in wait (min)",
    "comm_gate_wait_mean": "Commuter gate wait (min)",
    "comm_left_behind": "Commuters left behind",
    "revenue_commuter": "Commuter revenue ($)",
    "refunds": "Refunds ($)",
    "pax_in_system_end": "Passengers in system at T",
}
DIFF_COLS = [*PRINCIPAL, "comm_left_behind", "security_wait_mean_business"]
EFFECTS = [  # (label, from, to, extra lanes)
    ("Add a coach lane, no sharing (A2 − Baseline)", "baseline", "a2_coach3", 1),
    ("Add a coach lane, with sharing (A3 − A1)", "a1_share", "a3_coach3_share", 1),
    ("Turn sharing on, 2 coach lanes (A1 − Baseline)", "baseline", "a1_share", 0),
    ("Turn sharing on, 3 coach lanes (A3 − A2)", "a2_coach3", "a3_coach3_share", 0),
    ("Fourth coach lane instead of sharing (Check − A3)", "a3_coach3_share", "check_coach4", 1),
]
LANE_STEPS = [e for e in EFFECTS if e[3] > 0] + [
    ("A3 over Baseline (one lane plus sharing)", "baseline", "a3_coach3_share", 1),
]
ROBUST_P = {"p005": 0.05, None: 0.1, "p02": 0.2}
ROBUST_CONFIGS = ["baseline", "a1_share", "a2_coach3", "a3_coach3_share"]


def fmt(col: str, x: float) -> str:
    if col in ("profit", "revenue_commuter", "refunds"):
        return f"{x:,.0f}"
    if col.startswith("util_"):
        return f"{x:.3f}"
    if col in ("comm_left_behind", "pax_in_system_end"):
        return f"{x:,.0f}"
    return f"{x:,.1f}"


def wage(x: float) -> str:
    """Dollars per hour: whole dollars, or cents when the value is below $10 (avoids '-0')."""
    return f"{x:,.0f}" if abs(x) >= 10 else f"{x:.2f}"


def mean_hw(col: str, x) -> str:
    ci = confidence_interval(x)
    return f"{fmt(col, ci['mean'])} ± {fmt(col, ci['half_width'])}"


def diff_cell(col: str, a, b) -> str:
    """b − a, paired by replication, with * when the 95% CI excludes zero."""
    d = paired_difference_ci(a, b)
    sig = "*" if d["ci_low"] > 0 or d["ci_high"] < 0 else ""
    return f"{fmt(col, d['mean'])} ± {fmt(col, d['half_width'])}{sig}"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def label(stem: str) -> str:
    name, b, c, share = CONFIGS[stem]
    return f"{name} ({b}+{c}, sharing {share})"


def load(results: pathlib.Path, stem: str, tag: str | None = None) -> pd.DataFrame:
    path = results / (f"robust_{tag}_{stem}.csv" if tag else f"{stem}.csv")
    df = pd.read_csv(path).sort_values("replication").reset_index(drop=True)
    return df


def check_paired(frames: dict[str, pd.DataFrame]) -> int:
    """All runs must have the same N, replications 0..N−1 and the same base_seed (spec §6.2)."""
    ref = next(iter(frames.values()))
    for name, df in frames.items():
        if list(df["replication"]) != list(ref["replication"]) or set(df["base_seed"]) != set(ref["base_seed"]):
            raise SystemExit(f"{name}: replications or base_seed differ from the other runs")
    return len(ref)


def build(results: pathlib.Path, hours: float) -> str:
    runs = {s: load(results, s) for s in CONFIGS}
    n = check_paired(runs)
    out = [f"# Phase IV comparison tables\n",
           f"Generated by `scripts/compare_alternatives.py` from `{results}/`. "
           f"N = {n} replications per configuration, base_seed {runs['baseline']['base_seed'].iloc[0]}, "
           f"other_delay_prob 0.1 unless stated. Values are mean ± 95% half-width (t-based). "
           f"Differences are paired by replication; * = the 95% CI excludes zero.\n"]

    out.append("## Table 10.1: Principal KPIs\n")
    out.append(table(["Configuration", *PRINCIPAL.values()],
                     [[label(s), *(mean_hw(c, df[c]) for c in PRINCIPAL)] for s, df in runs.items()]))

    out.append("\n## Table 10.2: Secondary measures\n")
    out.append(table(["Configuration", *SECONDARY.values()],
                     [[CONFIGS[s][0], *(mean_hw(c, df[c]) for c in SECONDARY)] for s, df in runs.items()]))

    names = {**PRINCIPAL, **SECONDARY}
    out.append("\n## Table 10.3: Paired differences, configuration − Baseline\n")
    out.append(table(["Configuration", *(names[c] for c in DIFF_COLS)],
                     [[label(s), *(diff_cell(c, runs["baseline"][c], runs[s][c]) for c in DIFF_COLS)]
                      for s in CONFIGS if s != "baseline"]))

    out.append("\n## Table 10.4: Effects in the 2 × 2 design (paired differences)\n")
    out.append(table(["Change", *(names[c] for c in DIFF_COLS)],
                     [[lab, *(diff_cell(c, runs[a][c], runs[b][c]) for c in DIFF_COLS)]
                      for lab, a, b, _ in EFFECTS]))

    out.append(f"\n## Table 12.1: Break-even security wage per extra lane (D27)\n\n"
               f"Break-even wage = profit gain ÷ (extra lanes × {hours:g} h). An extra lane pays for "
               f"itself at any wage below this value.\n")
    rows = []
    for lab, a, b, lanes in LANE_STEPS:
        d = paired_difference_ci(runs[a]["profit"], runs[b]["profit"])
        per_h = lanes * hours
        w = [d[k] / per_h for k in ("mean", "ci_low", "ci_high")]
        rows.append([lab, f"{d['mean']:,.0f} ± {d['half_width']:,.0f}",
                     f"{wage(w[0])} ({wage(w[1])} to {wage(w[2])})"])
    out.append(table(["Step", "Profit gain per week ($)", "Break-even wage $/h (95% CI)"], rows))

    out.append("\n## Table 12.2: Robustness to the D4 assumption (other_delay_prob)\n\n"
               "Baseline value is 0.1. Coach check-in becomes overloaded at about p = 0.16 "
               "(DECISIONS.md, D4 resolution).\n")
    rows = []
    for tag, p in ROBUST_P.items():
        frames = {s: (runs[s] if tag is None else load(results, s, tag)) for s in ROBUST_CONFIGS}
        check_paired({**frames, "baseline_main": runs["baseline"]})
        for s, df in frames.items():
            diff = "—" if s == "baseline" else diff_cell("prov_pct_missed", frames["baseline"]["prov_pct_missed"],
                                                          df["prov_pct_missed"])
            rows.append([f"{p:g}", CONFIGS[s][0],
                         *(mean_hw(c, df[c]) for c in ("security_wait_mean_coach", "checkin_wait_mean_coach",
                                                        "prov_pct_missed")),
                         diff, mean_hw("profit", df["profit"]), mean_hw("comm_left_behind", df["comm_left_behind"])])
    out.append(table(["p", "Config", "Coach security wait (min)", "Coach check-in wait (min)",
                      "Provincial missed (%)", "Missed vs Baseline (same p)", "Profit ($)",
                      "Commuters left behind"], rows))
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--out", help="Markdown file to write (default: <results-dir>/phase4_tables.md)")
    args = ap.parse_args(argv)

    results = pathlib.Path(args.results_dir)
    hours = load_config("config/baseline.yaml")["simulation"]["horizon_days"] * 24
    text = build(results, hours)
    out = pathlib.Path(args.out) if args.out else results / "phase4_tables.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
