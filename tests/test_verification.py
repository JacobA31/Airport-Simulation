"""Verification evidence for report §7.1 (Person A, Phase III).

* Queue/resource-state assertions after every event and passenger conservation
  at the end of the run, over several independent baseline replications and
  the operating alternatives' flag combinations (see also test_model_smoke.py).
* The conservation checker itself is tested on rows that break an identity,
  so a passing check is meaningful.
"""

from __future__ import annotations

import pytest

from airport_sim.checks import conservation_violations
from airport_sim.model import run_replication
from tests.helpers import baseline_cfg, checked_run


@pytest.mark.parametrize("rep", range(5))
def test_state_invariants_and_conservation_over_replications(rep):
    res, m = checked_run(baseline_cfg(), rep=rep)
    assert res["pax_in_system_end"] > 0          # baseline ends with passengers still queued
    assert len(m.passengers) == res["comm_arrived"] + res["prov_arrived"]


@pytest.mark.parametrize("overrides", [
    {"operations__checkin_counters__coach": 5, "operations__security_lanes__coach": 4},
    {"operations__checkin_cross_use": "both", "operations__security_cross_use": "both"},
    {"operations__missed_pax_policy": "leave_at_departure"},
], ids=["more_capacity", "sharing", "leave_at_departure"])
def test_common_random_numbers_across_policies(overrides):
    """A policy change leaves every passenger's arrival time and random requirements unchanged (D15),
    which is what makes paired comparisons of alternatives valid."""
    def draws(cfg):
        _, m = checked_run(cfg, rep=0)
        return [(p.ptype, p.cabin, p.t_arrive, p.bags, p.checkin_time, p.security_time, p.lead_time)
                for p in m.passengers]
    assert draws(baseline_cfg(**overrides)) == draws(baseline_cfg())


@pytest.mark.parametrize("column,delta", [
    ("comm_boarded", 1), ("prov_caught", -1), ("prov_missed_left", 1),
    ("end_gate_commuters", 1), ("prov_arrived", -1),
])
def test_checker_detects_broken_identities(column, delta):
    row = run_replication(baseline_cfg(simulation__horizon_days=1), 0)
    assert conservation_violations(row) == []
    broken = {**row, column: row[column] + delta}
    assert conservation_violations(broken) != []


def test_checker_flags_security_without_checkin():
    row = run_replication(baseline_cfg(simulation__horizon_days=1), 0)
    broken = {**row, "security_completed": row["checkin_completed"] + 1}
    assert conservation_violations(broken) != []
    assert conservation_violations(broken, all_use_checkin=False) == []
