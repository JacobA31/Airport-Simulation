"""Event types and the future event list (D1, D9)."""

from __future__ import annotations

import heapq
import itertools
from enum import Enum


class EventType(Enum):
    SECURITY_END = "SECURITY_END"
    CHECKIN_END = "CHECKIN_END"
    COMMUTER_ARRIVAL = "COMMUTER_ARRIVAL"
    PROVINCIAL_ARRIVAL = "PROVINCIAL_ARRIVAL"
    COMMUTER_DEPARTURE = "COMMUTER_DEPARTURE"
    PROVINCIAL_DEPARTURE = "PROVINCIAL_DEPARTURE"
    END = "END"


# Tie-breaking rule for events at the same time (D9): lower number is processed
# first; equal priorities are processed in the order they were scheduled.
# SECURITY_END before the departures makes "completes security at or before
# the departure time catches the flight" hold exactly.
PRIORITY = {
    EventType.SECURITY_END: 1,
    EventType.CHECKIN_END: 2,
    EventType.COMMUTER_ARRIVAL: 3,
    EventType.PROVINCIAL_ARRIVAL: 3,
    EventType.COMMUTER_DEPARTURE: 4,
    EventType.PROVINCIAL_DEPARTURE: 4,
    EventType.END: 5,
}


class EventList:
    """Future event list: a binary heap ordered by (time, priority, sequence number)."""

    def __init__(self) -> None:
        self._heap: list = []
        self._seq = itertools.count()

    def schedule(self, time: float, etype: EventType, payload=None) -> None:
        # The sequence number is unique, so tuples never compare etype or payload.
        heapq.heappush(self._heap, (time, PRIORITY[etype], next(self._seq), etype, payload))

    def pop(self) -> tuple[float, EventType, object]:
        time, _, _, etype, payload = heapq.heappop(self._heap)
        return time, etype, payload

    def __len__(self) -> int:
        return len(self._heap)
