"""Unit tests for airport_sim/variates.py (verification evidence for report §5/§7).

Approach: draw a large sample from each variate generator and check that the
sample mean matches the theoretical mean of the intended distribution. A fixed
seed makes the tests reproducible, and the tolerance is expressed in standard
errors so a correct generator passes reliably while a real mistake is caught.
"""

import math
from statistics import NormalDist

import numpy as np
import pytest

from airport_sim.rng import RandomStreams
from airport_sim.variates import Variates

# Baseline inputs from the project handout. Keys match what Variates reads
# from the inputs section of config.yaml.
CFG = {
    "commuter_arrival_rate_per_hour": 40, # Poisson rate (passengers/hour)
    "provincial_demand": {
        "seats": 
            {"business": 40, "coach": 140},
        "occupancy_prob": 
            {"business": 0.75, "coach": 0.85},
    },
    "provincial_lead_time": { # truncated normal, minutes before departure
        "mean_min": 75, 
        "variance_min2": 50, 
        "lower_min": 0, 
        "upper_min": 180,
    },
    "bags_pmf": # P(B = 0), P(B = 1), P(B = 2)
        {"commuter": [0.70, 0.25, 0.05], 
        "provincial": [0.30, 0.50, 0.20]},
    "checkin": {
        "boarding_pass_mean_min": 2, # Exp, mean 2 min
        "per_bag_mean_min": 1, # one Exp(mean 1 min) per checked bag
        "other_delay_prob": 1.0, #other delays
        "other_delay_mean_min": 3,  #Exp, mean 3 min
    },
    "security_mean_min": 3, # Exp, mean 3 min
}
# samples per test, large so that standard error is small
N = 200_000 


def make(cfg=CFG, seed=2026):
    return Variates(cfg, RandomStreams(seed, 0))


def assert_mean(samples, theoretical, z=4.0):
    x = np.asarray(samples, dtype=float)
    se = x.std(ddof=1) / math.sqrt(len(x))
    assert abs(x.mean() - theoretical) < z * se, (x.mean(), theoretical, se)

# Poisson arrivals at 40/hour -> exponential gaps with mean 60/40 = 1.5 min.
def test_commuter_interarrival_mean():
    v = make()
    assert_mean([v.commuter_interarrival() for _ in range(N)], 60 / 40)


@pytest.mark.parametrize("cabin,theoretical_mean", [("business", 40 * 0.75), ("coach", 140 * 0.85)])
# Binomial(seats, occupancy) has mean seats * p: 30 business, 119 coach.
def test_provincial_booked_mean(cabin, theoretical_mean):
    v = make()
    assert_mean([v.provincial_booked(cabin) for _ in range(N)], theoretical_mean)


@pytest.mark.parametrize("ptype,theoretical_mean", [("commuter", 0.35), ("provincial", 0.90)])
# E[B] = 0*p0 + 1*p1 + 2*p2: commuter 0.25 + 0.10 = 0.35, provincial 0.50 + 0.40 = 0.90.
def test_bags_mean_and_support(ptype, theoretical_mean):
    v = make()
    x = [v.bags(ptype) for _ in range(N)]
    assert set(x) <= {0, 1, 2}
    assert_mean(x, theoretical_mean)


@pytest.mark.parametrize("b", [0, 1, 2])
# Mean of the sum of independent components: boarding pass (2) + b bags (1 each)
# + other delays (3) = 2 + b + 3 minutes.
def test_checkin_mean(b):
    v = make()
    assert_mean([v.checkin_time(b) for _ in range(N)], 2 + b * 1 + 3)

# Exponential screening time with mean 3 min.
def test_security_mean():
    v = make()
    assert_mean([v.security_time() for _ in range(N)], 3)


def test_lead_time_truncated_normal():
    v = make()
    x = np.array([v.provincial_lead_time() for _ in range(N)])
    p = CFG["provincial_lead_time"]
    
    # 1) Every variate must respect the truncation limits.
    assert x.min() >= p["lower_min"] and x.max() <= p["upper_min"]

    # 2) Theoretical mean of a truncated normal:
    #    mu + sigma * (pdf(alpha) - pdf(beta)) / (cdf(beta) - cdf(alpha)).
    sd = math.sqrt(p["variance_min2"])
    nd = NormalDist()
    al, be = (p["lower_min"] - 75) / sd, (p["upper_min"] - 75) / sd
    z = nd.cdf(be) - nd.cdf(al)
    theo_mean = 75 + sd * (nd.pdf(al) - nd.pdf(be)) / z
    assert_mean(x, theo_mean)

    # 3) Tail check: the fraction arriving more than 90 min early drives refunds.
    #    Theory is about 1.7%; the tolerance is absolute (0.2 percentage points).
    theo_tail = (nd.cdf(be) - nd.cdf((90 - 75) / sd)) / z
    assert abs((x > 90).mean() - theo_tail) < 0.002


# Extreme-condition test: a rate of 0 means no commuter ever arrives, so the
# next interarrival time is infinite.
def test_zero_commuter_rate():
    cfg = {**CFG, "commuter_arrival_rate_per_hour": 0}
    assert make(cfg).commuter_interarrival() == math.inf