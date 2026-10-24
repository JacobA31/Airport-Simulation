"""Entities: passengers and provincial flights (conceptual model §4.2)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Passenger.status values, in the order a passenger normally moves through them.
CHECKIN_QUEUE = "checkin_queue"
CHECKIN_SERVICE = "checkin_service"
SECURITY_QUEUE = "security_queue"
SECURITY_SERVICE = "security_service"
GATE = "gate"
BOARDED = "boarded"
LEFT = "left"          # left the airport without flying (missed provincial passenger)


# eq=False: passengers compare by identity, so deque.remove() removes this exact passenger.
@dataclass(eq=False, slots=True)
class Passenger:
    pid: int
    ptype: str                       # "commuter" | "provincial"
    cabin: str                       # "business" | "coach"
    t_arrive: float
    bags: int
    checkin_time: float              # S1, drawn at creation
    security_time: float             # S2, drawn at creation
    flight: ProvincialFlight | None = None   # provincial only
    lead_time: float | None = None           # provincial only: D - t_arrive
    status: str = ""
    server_pool: str | None = None   # pool of the server currently serving this passenger
    t_q1: float | None = None        # check-in: join queue, start, end
    t_s1: float | None = None
    t_e1: float | None = None
    t_q2: float | None = None        # security: join queue, start, end
    t_s2: float | None = None
    t_e2: float | None = None
    t_gate: float | None = None
    t_board: float | None = None
    missed: bool = False
    refunded: bool = False
    leave_after_service: bool = False   # set only under missed_pax_policy = leave_at_departure
    times_left_behind: int = 0          # commuters: full flights that left without them


@dataclass(eq=False, slots=True)
class ProvincialFlight:
    fid: int
    departure: float
    booked: dict                                  # cabin -> number of booked passengers
    passengers: list = field(default_factory=list)  # booked passengers who have arrived
    at_gate: list = field(default_factory=list)     # cleared security, waiting to board
    departed: bool = False

    @property
    def n_booked(self) -> int:
        return sum(self.booked.values())
