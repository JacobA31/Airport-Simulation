"""Smoke tests for the simulation core (Person A, Phase II).

The formal verification evidence for report §7 (Phase III) builds on these.
"""

from __future__ import annotations

import math

import pytest

from airport_sim.config import ConfigError, apply_overrides
from airport_sim.model import run_replication
from tests.helpers import FixedVariates, baseline_cfg, checked_run


# ------------------------------------------------------------- whole-model runs
@pytest.mark.parametrize("overrides", [
    {},
    {"operations__checkin_cross_use": "business_to_coach", "operations__security_cross_use": "business_to_coach"},
    {"operations__checkin_cross_use": "both", "operations__security_cross_use": "both"},
    {"operations__missed_pax_policy": "leave_at_departure"},
    {"operations__commuter_zero_bag_skips_checkin": True},
    {"inputs__commuter_arrival_rate_per_hour": 0},
    {"operations__checkin_counters__coach": 5, "operations__security_lanes__coach": 6},
    {"flights__commuter__seats": 20, "operations__checkin_counters__coach": 5,
     "operations__security_lanes__coach": 6},
], ids=["baseline", "share_b2c", "share_both", "leave_at_departure", "skip_zero_bag",
        "no_commuters", "high_capacity", "gate_bottleneck"])
def test_invariants_and_conservation(overrides):
    res, m = checked_run(baseline_cfg(**overrides))
    assert res["n_comm_flights"] == 168 and res["n_prov_flights"] == 28


def test_same_seed_reproduces_and_replications_differ():
    cfg = baseline_cfg()
    a, b, c = run_replication(cfg, 0), run_replication(cfg, 0), run_replication(cfg, 1)
    assert a == {**b}
    assert a["comm_arrived"] != c["comm_arrived"] or a["prov_booked"] != c["prov_booked"]


def test_finance_identities():
    cfg = baseline_cfg()
    res, m = checked_run(cfg)
    fp, fc = cfg["flights"]["provincial"], cfg["flights"]["commuter"]
    booked = {c: sum(f.booked[c] for f in m.prov_flights) for c in ("business", "coach")}
    assert res["revenue_commuter"] == res["comm_boarded"] * fc["fare"]
    assert res["revenue_provincial"] == booked["business"] * fp["fare"]["business"] + booked["coach"] * fp["fare"]["coach"]
    assert res["revenue_gross"] == res["revenue_commuter"] + res["revenue_provincial"]
    assert res["refunds"] == res["refund_value"]
    assert res["revenue_net"] == res["revenue_gross"] - res["refunds"]
    assert res["op_cost"] == 168 * fc["operating_cost"] + 28 * fp["operating_cost"]
    assert res["staffing_cost"] == pytest.approx(4 * 35 * 168)
    assert res["profit"] == pytest.approx(res["revenue_net"] - res["op_cost"] - res["staffing_cost"])
    assert res["staffing_ratio"] == pytest.approx(res["staffing_cost"] / res["revenue_net"])
    assert res["staffing_ok"] == (res["staffing_ratio"] <= 0.05)


def test_refund_rule():
    res, m = checked_run(baseline_cfg())
    fares = {"business": 1000, "coach": 500}
    prov = [p for p in m.passengers if p.ptype == "provincial"]
    assert all(p.refunded == (p.missed and p.lead_time >= 90) for p in prov)
    assert res["refund_count"] == sum(p.refunded for p in prov)
    assert res["refund_value"] == sum(fares[p.cabin] for p in prov if p.refunded)


def test_server_sharing_happens_only_when_enabled():
    res_none, _ = checked_run(baseline_cfg())
    res_both, _ = checked_run(baseline_cfg(operations__checkin_cross_use="both", operations__security_cross_use="both"))
    assert res_none["checkin_cross_served"] == res_none["security_cross_served"] == 0
    assert res_both["checkin_cross_served"] > 0 and res_both["security_cross_served"] > 0


# ---------------------------------------------------- deterministic logic tests
def one_day(**overrides) -> dict:
    return baseline_cfg(simulation__horizon_days=1, **overrides)


def test_security_end_exactly_at_departure_catches_flight():
    """D9: arrival at D-75, check-in 30, security 45 -> security ends exactly at D -> caught."""
    v = FixedVariates(booked={"business": 1, "coach": 1}, lead=75.0, checkin=30.0, security=45.0)
    res, m = checked_run(one_day(), variates=v)
    assert res["prov_booked"] == 8 and res["prov_caught"] == 8 and res["prov_missed"] == 0
    assert all(p.t_e2 == p.flight.departure for p in m.passengers)


def test_security_end_just_after_departure_misses_without_refund():
    v = FixedVariates(booked={"business": 1, "coach": 1}, lead=75.0, checkin=30.0, security=45.001)
    res, m = checked_run(one_day(), variates=v)
    assert res["prov_caught"] == 0 and res["prov_missed"] == 8
    assert res["refund_count"] == 0                     # arrived 75 < 90 min early
    assert res["prov_missed_left"] == 6                 # flight 4 departs at T: its 2 are still in security


def test_missed_after_arriving_90_min_early_is_refunded():
    v = FixedVariates(booked={"business": 1, "coach": 1}, lead=90.0, checkin=50.0, security=50.0)
    res, _ = checked_run(one_day(), variates=v)
    assert res["prov_missed"] == 8 and res["refund_count"] == 8
    assert res["refund_value"] == 4 * (1000 + 500)


def test_commuter_gate_capacity_and_fifo():
    """One commuter per minute, 1-min services, 40 seats, flights at :30 -> hand-calculable boarding."""
    v = FixedVariates(interarrival=1.0, checkin=1.0, security=1.0)
    res, m = checked_run(one_day(flights__commuter__seats=40), variates=v)
    # Arrivals at t = 1, 2, ..., 1439; each reaches the gate 2 min later (no queues at 1/min).
    assert res["comm_arrived"] == 1439
    assert res["checkin_wait_mean_coach"] == 0 and res["security_wait_mean_coach"] == 0
    # The 00:30 flight takes the 28 commuters at the gate by t = 30 (arrivals 1..28); later flights take 40.
    boarded = sorted((p for p in m.passengers if p.t_board is not None), key=lambda p: p.pid)
    assert [p.t_board for p in boarded[:28]] == [30.0] * 28
    assert all(a.t_board <= b.t_board for a, b in zip(boarded, boarded[1:]))   # FIFO by gate arrival
    assert res["comm_left_behind"] > 0                  # 60 arrive per hour, 40 seats


def test_zero_arrivals_extreme_case():
    v = FixedVariates()                                  # no commuters, no provincial bookings
    res, _ = checked_run(one_day(), variates=v)
    assert res["comm_arrived"] == res["prov_booked"] == res["pax_in_system_end"] == 0
    assert res["util_checkin_coach"] == res["util_security_coach"] == 0
    assert math.isnan(res["checkin_wait_mean_coach"]) and math.isnan(res["prov_pct_missed"])
    assert res["op_cost"] == 24 * 1500 + 4 * 12000      # flights still operate empty (D13)


# ------------------------------------------------------------------ config checks
def test_config_rejects_too_many_counters_and_unknown_keys():
    with pytest.raises(ConfigError):
        baseline_cfg(operations__checkin_counters__coach=6)        # 1 + 6 > 6
    with pytest.raises(ConfigError):
        apply_overrides(baseline_cfg(), {"operations.checkin_counter.coach": 3})
