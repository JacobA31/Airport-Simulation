"""Shared test helpers: an invariant-checking run and a deterministic variates stub."""

from __future__ import annotations

import math

from airport_sim.config import CABINS, load_config
from airport_sim.entities import BOARDED, LEFT
from airport_sim.model import AirportModel
from airport_sim.rng import RandomStreams
from airport_sim.variates import Variates

BASELINE = "config/baseline.yaml"


def baseline_cfg(**overrides) -> dict:
    """Baseline config with overrides given as a__b__c=value (validated like any loaded config)."""
    return load_config(BASELINE, {k.replace("__", "."): v for k, v in overrides.items()})


def check_state(m: AirportModel, line: str, i: int) -> None:
    """Queue/resource-state invariants after event ``i`` (whole-queue scans every 100th event)."""
    for s, t_join in ((m.checkin, "t_q1"), (m.security, "t_q2")):
        for pool in CABINS:
            assert 0 <= s.busy[pool] <= s.capacity[pool], f"{s.name} {pool} busy out of range"
            if s.busy[pool] < s.capacity[pool]:          # no idle server while an eligible passenger waits
                assert all(not s.queue[c] for c in s.queues_for(pool)), f"{s.name}: idle {pool} server"
        if i % 100 == 0:
            for c in CABINS:                              # FIFO: each queue ordered by join time
                q = list(s.queue[c])
                assert all(getattr(a, t_join) <= getattr(b, t_join) for a, b in zip(q, q[1:]))
    if m.leave_at_departure and "PROVINCIAL_DEPARTURE" in line:
        for s in (m.checkin, m.security):
            for q in s.queue.values():
                assert not any(p.ptype == "provincial" and p.flight.departed for p in q)


def check_conservation(res: dict, m: AirportModel) -> None:
    """Every passenger is boarded, has left, or is still in the system; outcomes add up."""
    in_system = [p for p in m.passengers if p.status not in (BOARDED, LEFT)]
    assert res["comm_arrived"] == res["comm_boarded"] + res["comm_in_system_end"]
    assert res["prov_booked"] == res["prov_arrived"] == res["prov_caught"] + res["prov_missed"]
    assert res["prov_missed"] == res["prov_missed_left"] + res["prov_in_system_end"]
    assert res["pax_in_system_end"] == len(in_system) == sum(
        res[k] for k in ("end_checkin_waiting", "end_checkin_in_service", "end_security_waiting",
                         "end_security_in_service", "end_gate_commuters"))
    assert all(p.status != LEFT for p in m.passengers if p.ptype == "commuter")


def checked_run(cfg: dict, rep: int = 0, variates=None) -> tuple[dict, AirportModel]:
    """Run one replication, checking the state invariants after every event."""
    if variates is None:
        variates = Variates(cfg["inputs"], RandomStreams(cfg["simulation"]["base_seed"], rep))
    m = AirportModel(cfg, variates)
    events = iter(range(10**9))
    m.trace = lambda line: check_state(m, line, next(events))
    res = m.run()
    check_conservation(res, m)
    return res, m


class FixedVariates:
    """Deterministic stand-in with the Variates interface (D15) for hand-calculable tests."""

    def __init__(self, interarrival=math.inf, booked=None, lead=75.0, bags=0, checkin=1.0, security=1.0):
        self.interarrival = interarrival
        self.booked = booked or {"business": 0, "coach": 0}
        self.lead, self.n_bags, self.checkin, self.security = lead, bags, checkin, security

    def commuter_interarrival(self):
        return self.interarrival

    def provincial_booked(self, cabin):
        return self.booked[cabin]

    def provincial_lead_time(self):
        return self.lead

    def bags(self, ptype):
        return self.n_bags

    def checkin_time(self, bags):
        return self.checkin

    def security_time(self):
        return self.security
