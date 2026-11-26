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


# ------------------------------------------------ server-sharing rule (D20), used by A1 and A3
class _Pax:
    def __init__(self, cabin):
        self.cabin = cabin


def _security(cross_use):
    from airport_sim.stations import Station
    return Station("security", {"business": 1, "coach": 2}, cross_use)


def test_sharing_rule_own_pool_first_then_the_other():
    """D20 under 'both': a passenger tries their own pool first; a freed server takes its own queue first."""
    s = _security("both")
    assert s.idle_pool_for("coach") == "coach"           # own pool idle -> own pool
    s.start("coach", 0.0, "coach", 0.0)
    s.start("coach", 0.0, "coach", 0.0)
    assert s.idle_pool_for("coach") == "business"        # coach lanes full -> idle business lane
    s.start("business", 0.0, "coach", 0.0)
    assert s.cross_served == 1 and s.idle_pool_for("business") is None

    b, c1, c2 = _Pax("business"), _Pax("coach"), _Pax("coach")
    for p in (c1, b, c2):                                # coach c1 joins before business b
        s.enqueue(p, 1.0)
    s.release("business", 2.0)
    assert s.next_for("business", 2.0) is b              # business lane takes its own queue first
    s.start("business", 2.0, "business", 1.0)
    s.release("coach", 3.0)
    assert s.next_for("coach", 3.0) is c1                # coach lane: own queue, FIFO
    s.start("coach", 3.0, "coach", 2.0)
    s.release("business", 4.0)
    assert s.next_for("business", 4.0) is c2             # business queue empty -> takes coach
    s.start("business", 4.0, "coach", 3.0)
    assert s.cross_served == 2
    assert s.next_for("coach", 4.0) is None              # both queues empty


def test_no_sharing_without_the_flag():
    """Baseline (D7): a coach passenger never uses the idle business lane, and vice versa."""
    s = _security("none")
    s.start("coach", 0.0, "coach", 0.0)
    s.start("coach", 0.0, "coach", 0.0)
    assert s.idle_pool_for("coach") is None              # business lane idle, but not eligible
    s.enqueue(_Pax("coach"), 1.0)
    assert s.next_for("business", 1.0) is None
    assert s.idle_pool_for("business") == "business"
