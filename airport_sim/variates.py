"""Random-variate generators for the model's stochastic inputs.

# PLACEHOLDER — Person B replaces this module.
# Minimal stand-ins so the model can run before the real input models exist.
# Person B owns the final implementation, its unit tests against theoretical
# means, and the input-modelling write-up (report §5). Keep the interface (D15);
# all times are in minutes:
#
#     Variates(inputs_cfg: dict, streams: RandomStreams)
#     .commuter_interarrival() -> float
#     .provincial_booked(cabin: str) -> int        # cabin: "business" | "coach"
#     .provincial_lead_time() -> float              # minutes before departure
#     .bags(ptype: str) -> int                      # ptype: "commuter" | "provincial"
#     .checkin_time(bags: int) -> float             # sum of the check-in components
#     .security_time() -> float
#
# The model calls nothing else, so any object with these six methods can be
# passed in (e.g. a deterministic stub for hand-calculable tests).
"""

from __future__ import annotations

import math


class Variates:
    def __init__(self, inputs_cfg: dict, streams) -> None:
        self.cfg = inputs_cfg
        self._arrivals = streams.get("commuter_arrivals")
        self._load = streams.get("provincial_load")
        self._lead = streams.get("provincial_lead_time")
        self._bags = streams.get("bags")
        self._checkin = streams.get("checkin_service")
        self._security = streams.get("security_service")

    def commuter_interarrival(self) -> float:
        rate = self.cfg["commuter_arrival_rate_per_hour"]
        if rate <= 0:
            return math.inf            # no commuter arrivals (extreme-condition test)
        return self._arrivals.exponential(60.0 / rate)

    def provincial_booked(self, cabin: str) -> int:
        demand = self.cfg["provincial_demand"]
        return int(self._load.binomial(demand["seats"][cabin], demand["occupancy_prob"][cabin]))

    def provincial_lead_time(self) -> float:
        # PLACEHOLDER: acceptance-rejection. The chosen final method is inverse
        # transform (D11), to be implemented by Person B.
        p = self.cfg["provincial_lead_time"]
        sd = math.sqrt(p["variance_min2"])
        while True:
            x = self._lead.normal(p["mean_min"], sd)
            if p["lower_min"] <= x <= p["upper_min"]:
                return float(x)

    def bags(self, ptype: str) -> int:
        pmf = self.cfg["bags_pmf"][ptype]
        u = self._bags.random()
        return 0 if u < pmf[0] else (1 if u < pmf[0] + pmf[1] else 2)

    def checkin_time(self, bags: int) -> float:
        # PLACEHOLDER: independent components; one Exp(per_bag_mean) per bag (A6).
        c = self.cfg["checkin"]
        rng = self._checkin
        total = rng.exponential(c["boarding_pass_mean_min"])
        for _ in range(bags):
            total += rng.exponential(c["per_bag_mean_min"])
        if rng.random() < c["other_delay_prob"]:
            total += rng.exponential(c["other_delay_mean_min"])
        return float(total)

    def security_time(self) -> float:
        return float(self._security.exponential(self.cfg["security_mean_min"]))
