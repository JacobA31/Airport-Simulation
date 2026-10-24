"""Statistics collectors: time-weighted (queue lengths, busy servers) and tallies (waits)."""

from __future__ import annotations

import math


class TimeWeighted:
    """Piecewise-constant quantity x(t); accumulates the area under x and its maximum."""

    __slots__ = ("value", "last_t", "area", "max")

    def __init__(self, value: float = 0, t0: float = 0.0) -> None:
        self.value = value
        self.last_t = t0
        self.area = 0.0
        self.max = value

    def update(self, t: float, value: float) -> None:
        """Record that x changes to ``value`` at time ``t``."""
        self.area += self.value * (t - self.last_t)
        self.last_t = t
        self.value = value
        if value > self.max:
            self.max = value

    def mean(self, t_end: float) -> float:
        """Time average of x over [0, t_end] (does not modify the collector)."""
        if t_end <= 0:
            return math.nan
        return (self.area + self.value * (t_end - self.last_t)) / t_end


class Tally:
    """Observation-based statistic (e.g. one waiting time per passenger)."""

    __slots__ = ("n", "total", "max")

    def __init__(self) -> None:
        self.n = 0
        self.total = 0.0
        self.max = math.nan

    def record(self, x: float) -> None:
        self.n += 1
        self.total += x
        if self.n == 1 or x > self.max:
            self.max = x

    def mean(self) -> float:
        return self.total / self.n if self.n else math.nan
