"""A processing station (check-in or security): two server pools and two FIFO queues.

The station only keeps state and statistics; the model decides when service
starts and ends and schedules the completion events.
"""

from __future__ import annotations

from collections import deque

from .config import CABINS
from .stats import Tally, TimeWeighted


def _other(cabin: str) -> str:
    return "coach" if cabin == "business" else "business"


class Station:
    def __init__(self, name: str, capacity: dict, cross_use: str = "none") -> None:
        self.name = name
        self.capacity = {c: int(capacity[c]) for c in CABINS}
        self.cross_use = cross_use
        self.queue = {c: deque() for c in CABINS}
        self.busy = {c: 0 for c in CABINS}
        self.q_len = {c: TimeWeighted() for c in CABINS}      # number waiting, per queue
        self.busy_tw = {c: TimeWeighted() for c in CABINS}    # number busy, per server pool
        self.wait = {c: Tally() for c in CABINS}              # waits by passenger cabin
        self.started = 0
        self.completed = 0
        self.cross_served = 0      # passengers served by the other class's pool (sharing modes only)

    # ---------------------------------------------------- server-sharing rule (D7, D20)
    def pools_for(self, cabin: str) -> tuple[str, ...]:
        """Server pools a passenger of ``cabin`` may use, in order of preference."""
        if self.cross_use == "both" or (self.cross_use == "business_to_coach" and cabin == "business"):
            return (cabin, _other(cabin))
        return (cabin,)

    def queues_for(self, pool: str) -> tuple[str, ...]:
        """Queues a freed server of ``pool`` takes passengers from, in order of preference."""
        if self.cross_use == "both" or (self.cross_use == "business_to_coach" and pool == "coach"):
            return (pool, _other(pool))
        return (pool,)

    def idle_pool_for(self, cabin: str) -> str | None:
        for pool in self.pools_for(cabin):
            if self.busy[pool] < self.capacity[pool]:
                return pool
        return None

    # --------------------------------------------------------------- state changes
    def enqueue(self, p, t: float) -> None:
        q = self.queue[p.cabin]
        q.append(p)
        self.q_len[p.cabin].update(t, len(q))

    def start(self, pool: str, t: float, cabin: str, wait: float) -> None:
        """A server of ``pool`` starts serving a ``cabin`` passenger who waited ``wait``."""
        assert self.busy[pool] < self.capacity[pool], f"{self.name}: no idle {pool} server"
        self.busy[pool] += 1
        self.busy_tw[pool].update(t, self.busy[pool])
        self.wait[cabin].record(wait)
        self.started += 1
        if pool != cabin:
            self.cross_served += 1

    def release(self, pool: str, t: float) -> None:
        assert self.busy[pool] > 0, f"{self.name}: releasing an idle {pool} server"
        self.busy[pool] -= 1
        self.busy_tw[pool].update(t, self.busy[pool])
        self.completed += 1

    def next_for(self, pool: str, t: float):
        """Remove and return the next passenger a freed ``pool`` server should serve, or None."""
        for cabin in self.queues_for(pool):
            q = self.queue[cabin]
            if q:
                p = q.popleft()
                self.q_len[cabin].update(t, len(q))
                return p
        return None

    def remove(self, p, t: float) -> None:
        """Take a waiting passenger out of the queue (reneging under leave_at_departure)."""
        q = self.queue[p.cabin]
        q.remove(p)
        self.q_len[p.cabin].update(t, len(q))

    # ------------------------------------------------------------------ reporting
    def n_waiting(self) -> int:
        return sum(len(q) for q in self.queue.values())

    def n_in_service(self) -> int:
        return sum(self.busy.values())

    def snapshot(self) -> str:
        """Compact state for event traces, e.g. 'q 0/5 busy 1/1 3/3'."""
        return (f"q {len(self.queue['business'])}/{len(self.queue['coach'])} "
                f"busy {self.busy['business']}/{self.capacity['business']} "
                f"{self.busy['coach']}/{self.capacity['coach']}")

    def kpis(self, T: float) -> dict:
        out = {}
        for c in CABINS:
            out[f"{self.name}_wait_mean_{c}"] = self.wait[c].mean()
            out[f"{self.name}_q_avg_{c}"] = self.q_len[c].mean(T)
            out[f"{self.name}_q_max_{c}"] = self.q_len[c].max
        for c in CABINS:
            cap = self.capacity[c]
            out[f"util_{self.name}_{c}"] = self.busy_tw[c].mean(T) / cap if cap else float("nan")
        return out
