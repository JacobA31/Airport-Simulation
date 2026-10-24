"""Event-scheduling model of SFMA passenger processing (conceptual model §4.5).

One ``AirportModel`` object is one replication. Each event type has one
routine (``_commuter_arrival``, ``_checkin_end``, ...) that changes the state
and schedules future events, exactly as drawn in the event graph
(docs/des_diagram.md).
"""

from __future__ import annotations

import math
from collections import Counter, deque

from . import finance
from .config import CABINS, horizon_minutes
from .entities import (BOARDED, CHECKIN_QUEUE, CHECKIN_SERVICE, GATE, LEFT, SECURITY_QUEUE,
                       SECURITY_SERVICE, Passenger, ProvincialFlight)
from .events import EventList, EventType
from .stations import Station
from .stats import Tally, TimeWeighted


def fmt_clock(t: float) -> str:
    """Minutes since Monday 00:00 -> 'd1 06:30:00'."""
    day, rem = divmod(t, 1440.0)
    h, rem = divmod(rem, 60.0)
    m, s = divmod(rem * 60.0, 60.0)
    return f"d{int(day) + 1} {int(h):02d}:{int(m):02d}:{s:04.1f}"


class AirportModel:
    def __init__(self, cfg: dict, variates, trace=None) -> None:
        self.cfg = cfg
        self.v = variates
        self.trace = trace                 # callable(str) or None
        self.T = horizon_minutes(cfg)
        self.clock = 0.0
        self.fel = EventList()
        self.n = Counter()                 # cumulative counters
        self.money = Counter()             # financial accumulators ($)
        self.passengers: list[Passenger] = []
        self.prov_flights: list[ProvincialFlight] = []
        ops = cfg["operations"]
        self.checkin = Station("checkin", ops["checkin_counters"], ops["checkin_cross_use"])
        self.security = Station("security", ops["security_lanes"], ops["security_cross_use"])
        self.skip_zero_bag = ops["commuter_zero_bag_skips_checkin"]
        self.leave_at_departure = ops["missed_pax_policy"] == "leave_at_departure"
        self.gate: deque[Passenger] = deque()      # commuter gate pool, FIFO by gate arrival (D8)
        self.gate_len = TimeWeighted()
        self.gate_wait = Tally()
        self._handlers = {
            EventType.COMMUTER_ARRIVAL: self._commuter_arrival,
            EventType.PROVINCIAL_ARRIVAL: self._provincial_arrival,
            EventType.CHECKIN_END: self._checkin_end,
            EventType.SECURITY_END: self._security_end,
            EventType.COMMUTER_DEPARTURE: self._commuter_departure,
            EventType.PROVINCIAL_DEPARTURE: self._provincial_departure,
            EventType.END: self._end,
        }

    # ------------------------------------------------------------------ run loop
    def run(self) -> dict:
        self._initialize()
        while self.fel:
            t, etype, payload = self.fel.pop()
            self.clock = t
            self._handlers[etype](payload)
            if etype is EventType.END:
                break
        return self._results()

    def _schedule(self, time: float, etype: EventType, payload=None) -> None:
        assert time >= self.clock, f"{etype} scheduled in the past ({time} < {self.clock})"
        self.fel.schedule(time, etype, payload)

    # ------------------------------------------------------------ initialisation
    def _initialize(self) -> None:
        a = self.v.commuter_interarrival()
        if a < self.T:
            self._schedule(a, EventType.COMMUTER_ARRIVAL)

        first_commuter = self.cfg["flights"]["commuter"]["first_departure_min"]
        if first_commuter <= self.T:
            self._schedule(first_commuter, EventType.COMMUTER_DEPARTURE)

        # Provincial flights departing in (0, T]; bookings exist before t = 0 (D12, D18).
        fp = self.cfg["flights"]["provincial"]
        d = fp["first_departure_min"]
        while d <= self.T:
            booked = {cabin: self.v.provincial_booked(cabin) for cabin in CABINS}
            flight = ProvincialFlight(fid=len(self.prov_flights) + 1, departure=d, booked=booked)
            self.prov_flights.append(flight)
            for cabin in CABINS:
                for _ in range(booked[cabin]):
                    lead = self.v.provincial_lead_time()
                    self._schedule(d - lead, EventType.PROVINCIAL_ARRIVAL, (flight, cabin, lead))
            d += fp["interval_min"]
        if self.prov_flights:
            self._schedule(self.prov_flights[0].departure, EventType.PROVINCIAL_DEPARTURE, 0)

        self._schedule(self.T, EventType.END)

    # ------------------------------------------------------------ event routines
    def _commuter_arrival(self, _payload) -> None:
        p = self._new_passenger("commuter", "coach")
        self.n["comm_arrived"] += 1
        if self.skip_zero_bag and p.bags == 0:     # D5 flag, off at baseline
            self._join_security(p)
        else:
            self._join_checkin(p)
        self._log(EventType.COMMUTER_ARRIVAL, f"pax {p.pid} commuter bags={p.bags} -> {p.status}")
        a = self.v.commuter_interarrival()
        if self.clock + a < self.T:
            self._schedule(self.clock + a, EventType.COMMUTER_ARRIVAL)

    def _provincial_arrival(self, payload) -> None:
        flight, cabin, lead = payload
        p = self._new_passenger("provincial", cabin, flight=flight, lead_time=lead)
        flight.passengers.append(p)
        self.n["prov_arrived"] += 1
        self._join_checkin(p)
        self._log(EventType.PROVINCIAL_ARRIVAL,
                  f"pax {p.pid} {cabin} flight {flight.fid} lead={lead:.1f} bags={p.bags} -> {p.status}")

    def _checkin_end(self, p: Passenger) -> None:
        pool = p.server_pool
        p.t_e1 = self.clock
        p.server_pool = None
        self.checkin.release(pool, self.clock)
        nxt = self.checkin.next_for(pool, self.clock)
        if nxt is not None:
            self._start_checkin(nxt, pool)
        if p.leave_after_service:
            self._leave(p)                       # leave_at_departure: flight left during check-in
        else:
            self._join_security(p)
        self._log(EventType.CHECKIN_END, f"pax {p.pid} done ({pool} counter) -> {p.status}"
                  + (f"; next pax {nxt.pid}" if nxt else ""))

    def _security_end(self, p: Passenger) -> None:
        pool = p.server_pool
        p.t_e2 = self.clock
        p.server_pool = None
        self.security.release(pool, self.clock)
        nxt = self.security.next_for(pool, self.clock)
        if nxt is not None:
            self._start_security(nxt, pool)
        if p.ptype == "commuter":
            p.t_gate = self.clock
            p.status = GATE
            self.gate.append(p)
            self.gate_len.update(self.clock, len(self.gate))
        elif not p.flight.departed:
            # t <= D is guaranteed here: SECURITY_END is processed before a departure at the same time (D9).
            p.t_gate = self.clock
            p.status = GATE
            p.flight.at_gate.append(p)
        else:
            self._leave(p)                       # missed; the miss was recorded at the departure (D16)
        self._log(EventType.SECURITY_END, f"pax {p.pid} done ({pool} lane) -> {p.status}"
                  + (f"; next pax {nxt.pid}" if nxt else ""))

    def _commuter_departure(self, _payload) -> None:
        fc = self.cfg["flights"]["commuter"]
        k = min(fc["seats"], len(self.gate))
        for _ in range(k):
            p = self.gate.popleft()
            p.t_board = self.clock
            p.status = BOARDED
            self.gate_wait.record(self.clock - p.t_gate)
        self.gate_len.update(self.clock, len(self.gate))
        self.n["comm_boarded"] += k
        for p in self.gate:                      # still waiting: this full flight left them behind
            if p.times_left_behind == 0:
                self.n["comm_left_behind"] += 1
            p.times_left_behind += 1
            self.n["comm_left_behind_events"] += 1
        self.n["comm_flights"] += 1
        self.money["revenue_commuter"] += k * fc["fare"]          # commuters pay when they board (D13)
        self.money["op_cost"] += fc["operating_cost"]             # every scheduled flight, even if empty
        self._log(EventType.COMMUTER_DEPARTURE, f"boarded {k}, left behind {len(self.gate)}")
        nxt = self.clock + fc["interval_min"]
        if nxt <= self.T:
            self._schedule(nxt, EventType.COMMUTER_DEPARTURE)

    def _provincial_departure(self, idx: int) -> None:
        f = self.prov_flights[idx]
        # Lead times are >= 0 and arrivals precede departures at equal times, so all have arrived.
        assert len(f.passengers) == f.n_booked, f"flight {f.fid}: not all booked passengers arrived"
        for p in f.at_gate:
            p.t_board = self.clock
            p.status = BOARDED
        fp = self.cfg["flights"]["provincial"]
        missed = [p for p in f.passengers if p.status != BOARDED]
        for p in missed:                          # not through security by D (D16)
            p.missed = True
            if p.lead_time >= fp["refund_min_lead_min"]:
                p.refunded = True
                self.n["refund_count"] += 1
                self.money["refund_value"] += fp["fare"][p.cabin]
            if self.leave_at_departure:
                self._renege(p)
        f.departed = True
        self.n["prov_caught"] += len(f.at_gate)
        self.n["prov_missed"] += len(missed)
        self.n["prov_flights"] += 1
        # Seats are sold in advance: revenue for every booked seat; refunds are a separate line (D13).
        self.money["revenue_provincial"] += sum(f.booked[c] * fp["fare"][c] for c in CABINS)
        self.money["op_cost"] += fp["operating_cost"]
        self._log(EventType.PROVINCIAL_DEPARTURE,
                  f"flight {f.fid}: booked {f.n_booked}, caught {len(f.at_gate)}, missed {len(missed)}, "
                  f"refunds {sum(p.refunded for p in missed)}")
        if idx + 1 < len(self.prov_flights):
            self._schedule(self.prov_flights[idx + 1].departure, EventType.PROVINCIAL_DEPARTURE, idx + 1)

    def _end(self, _payload) -> None:
        self._log(EventType.END, "end of horizon")

    # ------------------------------------------------- station subroutines (§4.5)
    def _join_checkin(self, p: Passenger) -> None:
        p.t_q1 = self.clock
        pool = self.checkin.idle_pool_for(p.cabin)
        if pool is None:
            p.status = CHECKIN_QUEUE
            self.checkin.enqueue(p, self.clock)
        else:
            self._start_checkin(p, pool)

    def _start_checkin(self, p: Passenger, pool: str) -> None:
        p.t_s1 = self.clock
        p.status = CHECKIN_SERVICE
        p.server_pool = pool
        self.checkin.start(pool, self.clock, p.cabin, wait=p.t_s1 - p.t_q1)
        self._schedule(self.clock + p.checkin_time, EventType.CHECKIN_END, p)

    def _join_security(self, p: Passenger) -> None:
        p.t_q2 = self.clock
        pool = self.security.idle_pool_for(p.cabin)
        if pool is None:
            p.status = SECURITY_QUEUE
            self.security.enqueue(p, self.clock)
        else:
            self._start_security(p, pool)

    def _start_security(self, p: Passenger, pool: str) -> None:
        p.t_s2 = self.clock
        p.status = SECURITY_SERVICE
        p.server_pool = pool
        self.security.start(pool, self.clock, p.cabin, wait=p.t_s2 - p.t_q2)
        self._schedule(self.clock + p.security_time, EventType.SECURITY_END, p)

    def _renege(self, p: Passenger) -> None:
        """leave_at_departure (D21): waiting passengers leave now, those in service after it."""
        if p.status == CHECKIN_QUEUE:
            self.checkin.remove(p, self.clock)
            self._leave(p)
        elif p.status == SECURITY_QUEUE:
            self.security.remove(p, self.clock)
            self._leave(p)
        else:
            p.leave_after_service = True

    def _leave(self, p: Passenger) -> None:
        """A missed provincial passenger leaves the airport."""
        p.status = LEFT
        self.n["prov_missed_left"] += 1

    # ------------------------------------------------------------------ helpers
    def _new_passenger(self, ptype: str, cabin: str, flight=None, lead_time=None) -> Passenger:
        # All of a passenger's random requirements are drawn at creation (D15).
        bags = self.v.bags(ptype)
        p = Passenger(
            pid=len(self.passengers) + 1, ptype=ptype, cabin=cabin, t_arrive=self.clock,
            bags=bags, checkin_time=self.v.checkin_time(bags), security_time=self.v.security_time(),
            flight=flight, lead_time=lead_time,
        )
        self.passengers.append(p)
        return p

    def _log(self, etype: EventType, msg: str) -> None:
        if self.trace is not None:
            self.trace(f"{fmt_clock(self.clock)}  t={self.clock:9.3f}  {etype.value:<20} {msg:<48}"
                       f" | CI {self.checkin.snapshot()} | SC {self.security.snapshot()} | gate {len(self.gate)}")

    # ------------------------------------------------------------------ results
    def _results(self) -> dict:
        """KPI dict for one replication (names and definitions: conceptual model §4.8, D14)."""
        T = self.T
        booked = sum(f.n_booked for f in self.prov_flights)
        in_system = [p for p in self.passengers if p.status not in (BOARDED, LEFT)]
        comm_in_system = sum(1 for p in in_system if p.ptype == "commuter")
        return {
            # check-in and security: waits, queue lengths, utilisation
            **self.checkin.kpis(T),
            **self.security.kpis(T),
            # provincial service
            "prov_booked": booked,
            "prov_caught": self.n["prov_caught"],
            "prov_missed": self.n["prov_missed"],
            "prov_pct_missed": 100.0 * self.n["prov_missed"] / booked if booked else math.nan,
            "refund_count": self.n["refund_count"],
            "refund_value": self.money["refund_value"],
            # commuter service
            "comm_arrived": self.n["comm_arrived"],
            "comm_boarded": self.n["comm_boarded"],
            "comm_gate_wait_mean": self.gate_wait.mean(),
            "comm_left_behind": self.n["comm_left_behind"],
            "comm_left_behind_events": self.n["comm_left_behind_events"],
            # financial
            **finance.summarize(self.money, self.cfg, T),
            # end-of-run state and counts for conservation checks
            "pax_in_system_end": len(in_system),
            "comm_in_system_end": comm_in_system,
            "prov_in_system_end": len(in_system) - comm_in_system,
            "end_checkin_waiting": self.checkin.n_waiting(),
            "end_checkin_in_service": self.checkin.n_in_service(),
            "end_security_waiting": self.security.n_waiting(),
            "end_security_in_service": self.security.n_in_service(),
            "end_gate_commuters": len(self.gate),
            "prov_arrived": self.n["prov_arrived"],
            "prov_missed_left": self.n["prov_missed_left"],
            "checkin_completed": self.checkin.completed,
            "security_completed": self.security.completed,
            "checkin_cross_served": self.checkin.cross_served,
            "security_cross_served": self.security.cross_served,
            "comm_gate_q_avg": self.gate_len.mean(T),
            "comm_gate_q_max": self.gate_len.max,
            "n_comm_flights": self.n["comm_flights"],
            "n_prov_flights": self.n["prov_flights"],
        }


def run_replication(cfg: dict, replication: int = 0, *, variates=None, trace=None) -> dict:
    """Run one replication and return its KPI dict (one CSV row for the runner)."""
    if variates is None:
        from .rng import RandomStreams
        from .variates import Variates
        variates = Variates(cfg["inputs"], RandomStreams(cfg["simulation"]["base_seed"], replication))
    results = AirportModel(cfg, variates, trace=trace).run()
    return {"replication": replication, **results}
