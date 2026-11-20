"""Config overlays for policy alternatives (D24) and the optional security wage (D25)."""

from __future__ import annotations

from pathlib import Path

import pytest

from airport_sim.config import ConfigError, load_config
from airport_sim.model import run_replication
from tests.helpers import BASELINE, baseline_cfg

BASE = Path(BASELINE).resolve()


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_overlay_equals_baseline_with_the_same_overrides(tmp_path):
    alt = write(tmp_path / "alt.yaml", f"""
extends: {BASE}
operations:
  security_lanes:
    coach: 4
  security_cross_use: both
""")
    expected = baseline_cfg(operations__security_lanes__coach=4, operations__security_cross_use="both")
    assert load_config(alt) == expected
    assert load_config(alt)["operations"]["security_lanes"]["business"] == 1    # untouched sibling kept


def test_overlay_chain_and_command_line_overrides(tmp_path):
    a = write(tmp_path / "a.yaml", f"extends: {BASE}\noperations:\n  security_lanes:\n    coach: 3\n")
    b = write(tmp_path / "b.yaml", "extends: a.yaml\noperations:\n  security_cross_use: both\n")
    cfg = load_config(b, {"operations.security_lanes.coach": 5})
    assert cfg["operations"]["security_lanes"]["coach"] == 5
    assert cfg["operations"]["security_cross_use"] == "both"


def test_overlay_rejects_unknown_keys_and_cycles(tmp_path):
    typo = write(tmp_path / "typo.yaml", f"extends: {BASE}\noperations:\n  security_lane:\n    coach: 3\n")
    with pytest.raises(ConfigError, match="operations.security_lane"):
        load_config(typo)
    write(tmp_path / "x.yaml", "extends: y.yaml\n")
    write(tmp_path / "y.yaml", "extends: x.yaml\n")
    with pytest.raises(ConfigError, match="circular"):
        load_config(tmp_path / "x.yaml")


def test_overlay_is_validated(tmp_path):
    bad = write(tmp_path / "bad.yaml", f"extends: {BASE}\noperations:\n  checkin_counters:\n    coach: 6\n")
    with pytest.raises(ConfigError):                      # 1 + 6 counters > 6
        load_config(bad)


def test_security_wage_reduces_profit_but_not_the_checkin_ratio():
    day = {"simulation__horizon_days": 1}
    free = run_replication(baseline_cfg(**day), 0)
    paid = run_replication(baseline_cfg(finance__security_wage_per_hour=30, **day), 0)
    lanes, hours = 3, 24
    assert free["security_staffing_cost"] == 0
    assert paid["security_staffing_cost"] == pytest.approx(lanes * 30 * hours)
    assert paid["profit"] == pytest.approx(free["profit"] - lanes * 30 * hours)
    assert paid["staffing_ratio"] == free["staffing_ratio"]
    assert {k: v for k, v in paid.items() if k not in ("profit", "security_staffing_cost")} == \
           {k: v for k, v in free.items() if k not in ("profit", "security_staffing_cost")}
