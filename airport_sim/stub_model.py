"""FAKE model for developing runner/analysis before Person A's simulator exists.
Returns made-up KPI values"""
import numpy as np


def run_replication(cfg: dict, streams) -> dict:
    rng = streams.get("security_service")
    scale = cfg["inputs"]["commuter_arrival_rate_per_hour"] / 40.0   # so overrides show up
    return {
        "mean_security_wait_min": float(rng.gamma(25, 0.4) * scale),
        "pct_provincial_missed": float(np.clip(rng.normal(3.0 * scale, 0.8), 0, 100)),
        "security_utilization": float(np.clip(rng.normal(0.80 * scale, 0.03), 0, 1)),
        "total_profit": float(rng.normal(2.0e6, 4.0e4)),
    }