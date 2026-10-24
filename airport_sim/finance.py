"""Per-replication financial accounting (D12, D13).

Revenue and operating cost are accumulated by the model at departure events:

* ``revenue_commuter``   - commuter fare for every commuter who boarded;
* ``revenue_provincial`` - fare for every booked seat on each provincial flight that departed;
* ``refund_value``       - fare of each missed provincial passenger who arrived >= 90 min early;
* ``op_cost``            - operating cost of every scheduled departure, even if empty.

Everything else is derived here.
"""

from __future__ import annotations

import math


def staffing_cost(cfg: dict, horizon_min: float) -> float:
    """Every check-in counter is staffed for the whole horizon (D12)."""
    counters = sum(cfg["operations"]["checkin_counters"].values())
    return counters * cfg["finance"]["checkin_wage_per_hour"] * horizon_min / 60.0


def summarize(money: dict, cfg: dict, horizon_min: float) -> dict:
    revenue_commuter = money.get("revenue_commuter", 0.0)
    revenue_provincial = money.get("revenue_provincial", 0.0)
    refunds = money.get("refund_value", 0.0)
    op_cost = money.get("op_cost", 0.0)
    staffing = staffing_cost(cfg, horizon_min)

    gross = revenue_commuter + revenue_provincial
    net = gross - refunds
    ratio = staffing / net if net > 0 else math.inf
    return {
        "revenue_commuter": revenue_commuter,
        "revenue_provincial": revenue_provincial,
        "revenue_gross": gross,
        "refunds": refunds,
        "revenue_net": net,
        "op_cost": op_cost,
        "staffing_cost": staffing,
        "profit": net - op_cost - staffing,
        "staffing_ratio": ratio,             # staffing cost / net ticket revenue
        "staffing_ok": ratio <= cfg["finance"]["staffing_ratio_limit"],
    }
