"""Random-variate generators for the model's stochastic inputs (report §5).

Interface (D15): all times are in minutes.

    Variates(inputs_cfg: dict, streams: RandomStreams)
    .commuter_interarrival() -> float             # Exp(mean = 60/rate), Poisson process
    .provincial_booked(cabin: str) -> int         # cabin: "business" | "coach"; Binomial(seats, p)
    .provincial_lead_time() -> float              # minutes before departure; truncated normal
    .bags(ptype: str) -> int                      # ptype: "commuter" | "provincial"; pmf on {0, 1, 2}
    .checkin_time(bags: int) -> float             # boarding pass + Exp per bag + other delays
    .security_time() -> float                     # Exp(mean)

The model calls nothing else, so any object with these six methods can be passed
in (e.g. a deterministic stub for hand-calculable tests).

Truncated normal, X ~ N(mu, sigma^2) restricted to [a, b]:
    alpha = (a - mu)/sigma, beta = (b - mu)/sigma
    X = mu + sigma * Phi^-1( Phi(alpha) + U * (Phi(beta) - Phi(alpha)) ),  U ~ U(0,1)
This uses exactly one uniform per variate, so the number of draws from the stream
does not depend on the values drawn (unlike acceptance-rejection).
"""

from __future__ import annotations

import math
from statistics import NormalDist

_STD_NORMAL = NormalDist()

class Variates:
    def __init__(self, inputs_cfg: dict, streams) -> None:
        self.cfg = inputs_cfg
        self._arrivals = streams.get("commuter_arrivals")
        self._load = streams.get("provincial_load")
        self._lead = streams.get("provincial_lead_time")
        self._bags = streams.get("bags")
        self._checkin = streams.get("checkin_service")
        self._security = streams.get("security_service")

        # Truncated-normal constants, computed once.
        p = inputs_cfg["provincial_lead_time"]
        if not p["lower_min"] < p["upper_min"]:
            raise ValueError("provincial_lead_time: lower_min must be < upper_min")
        if p["variance_min2"] <= 0:
            raise ValueError("provincial_lead_time: variance_min2 must be > 0")
        self._lt_mu = p["mean_min"]
        self._lt_sd = math.sqrt(p["variance_min2"])
        self._lt_lo, self._lt_hi = p["lower_min"], p["upper_min"]
        self._lt_cdf_lo = _STD_NORMAL.cdf((self._lt_lo - self._lt_mu) / self._lt_sd)
        self._lt_cdf_hi = _STD_NORMAL.cdf((self._lt_hi - self._lt_mu) / self._lt_sd)

        # Cumulative bag probabilities per passenger type.
        self._bag_cdf = {}
        for ptype, pmf in inputs_cfg["bags_pmf"].items():
            if len(pmf) != 3 or abs(sum(pmf) - 1.0) > 1e-9:
                raise ValueError(f"bags_pmf[{ptype!r}] must have 3 entries summing to 1")
            self._bag_cdf[ptype] = (pmf[0], pmf[0] + pmf[1])

    def commuter_interarrival(self) -> float:
        rate = self.cfg["commuter_arrival_rate_per_hour"]
        if rate <= 0:
            return math.inf            # no commuter arrivals (extreme-condition test)
        return self._arrivals.exponential(60.0 / rate)

    def provincial_booked(self, cabin: str) -> int:
        demand = self.cfg["provincial_demand"]
        return int(self._load.binomial(demand["seats"][cabin], demand["occupancy_prob"][cabin]))

    def provincial_lead_time(self) -> float:
        u = self._lead.random()
        p = self._lt_cdf_lo + u * (self._lt_cdf_hi - self._lt_cdf_lo)
        p = min(max(p, 1e-300), 1.0 - 1e-16)       # inv_cdf needs 0 < p < 1
        x = self._lt_mu + self._lt_sd * _STD_NORMAL.inv_cdf(p)
        return float(min(max(x, self._lt_lo), self._lt_hi))   # guard against rounding

    def bags(self, ptype: str) -> int:
        c0, c1 = self._bag_cdf[ptype]
        u = self._bags.random()
        return 0 if u < c0 else (1 if u < c1 else 2)

    def checkin_time(self, bags: int) -> float:
        c = self.cfg["checkin"]
        rng = self._checkin
        total = rng.exponential(c["boarding_pass_mean_min"])
        for _ in range(bags):
            total += rng.exponential(c["per_bag_mean_min"])
        p_other = c.get("other_delay_prob", 1.0)
        if p_other >= 1.0 or rng.random() < p_other:
            total += rng.exponential(c["other_delay_mean_min"])
        return float(total)

    def security_time(self) -> float:
        return float(self._security.exponential(self.cfg["security_mean_min"]))
