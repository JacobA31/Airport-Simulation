"""Load, override and validate the YAML configuration (D2).

The configuration is kept as a plain nested dict so that runners can copy it
and override single values with dotted keys, e.g.
``{"operations.checkin_counters.coach": 5}``.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import yaml

CABINS = ("business", "coach")
CROSS_USE_MODES = ("none", "business_to_coach", "both")
MISSED_PAX_POLICIES = ("continue", "leave_at_departure")
MIN_PER_DAY = 1440


class ConfigError(ValueError):
    """Raised when a configuration is missing a key or has an invalid value."""


def load_config(path: str | Path, overrides: dict | None = None) -> dict:
    """Read a YAML config, apply dotted-key overrides, validate, and return it."""
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if overrides:
        cfg = apply_overrides(cfg, overrides)
    validate_config(cfg)
    return cfg


def apply_overrides(cfg: dict, overrides: dict) -> dict:
    """Return a deep copy of ``cfg`` with each ``"a.b.c": value`` replaced.

    Only existing keys can be overridden, so a typo raises instead of silently
    adding an unused parameter.
    """
    out = copy.deepcopy(cfg)
    for dotted, value in overrides.items():
        *parents, leaf = dotted.split(".")
        node = out
        for key in parents:
            if not isinstance(node, dict) or key not in node:
                raise ConfigError(f"unknown config key: {dotted}")
            node = node[key]
        if not isinstance(node, dict) or leaf not in node:
            raise ConfigError(f"unknown config key: {dotted}")
        node[leaf] = value
    return out


def horizon_minutes(cfg: dict) -> float:
    return cfg["simulation"]["horizon_days"] * MIN_PER_DAY


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ConfigError(msg)


def _get(cfg: dict, dotted: str):
    node = cfg
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            raise ConfigError(f"missing config key: {dotted}")
        node = node[key]
    return node


def _pool_sizes_ok(name: str, pools: dict, cross_use: str) -> None:
    """Every passenger class must have at least one server it is allowed to use."""
    for cabin in CABINS:
        n = pools[cabin]
        _require(isinstance(n, int) and n >= 0, f"{name}.{cabin} must be a non-negative integer")
    if cross_use == "none":
        _require(pools["business"] >= 1 and pools["coach"] >= 1,
                 f"{name}: with cross_use 'none' each pool needs at least one server")
    elif cross_use == "business_to_coach":
        _require(pools["coach"] >= 1, f"{name}: coach passengers need at least one coach server")
    else:
        _require(pools["business"] + pools["coach"] >= 1, f"{name}: needs at least one server")


def validate_config(cfg: dict) -> None:
    """Check the keys and values the model relies on. Raises ConfigError."""
    T = _get(cfg, "simulation.horizon_days")
    _require(T > 0, "simulation.horizon_days must be positive")
    _get(cfg, "simulation.base_seed")

    ops = _get(cfg, "operations")
    for key in ("checkin_cross_use", "security_cross_use"):
        _require(ops.get(key) in CROSS_USE_MODES, f"operations.{key} must be one of {CROSS_USE_MODES}")
    _require(ops.get("missed_pax_policy") in MISSED_PAX_POLICIES,
             f"operations.missed_pax_policy must be one of {MISSED_PAX_POLICIES}")
    _require(isinstance(_get(cfg, "operations.commuter_zero_bag_skips_checkin"), bool),
             "operations.commuter_zero_bag_skips_checkin must be true or false")
    _pool_sizes_ok("operations.checkin_counters", _get(cfg, "operations.checkin_counters"),
                   ops["checkin_cross_use"])
    _pool_sizes_ok("operations.security_lanes", _get(cfg, "operations.security_lanes"),
                   ops["security_cross_use"])
    n_counters = sum(ops["checkin_counters"].values())
    _require(n_counters <= _get(cfg, "operations.max_checkin_counters"),
             f"{n_counters} check-in counters exceed operations.max_checkin_counters")

    for svc in ("commuter", "provincial"):
        _require(_get(cfg, f"flights.{svc}.interval_min") > 0, f"flights.{svc}.interval_min must be positive")
        _require(_get(cfg, f"flights.{svc}.first_departure_min") >= 0,
                 f"flights.{svc}.first_departure_min must be >= 0")
        _require(_get(cfg, f"flights.{svc}.operating_cost") >= 0, f"flights.{svc}.operating_cost must be >= 0")
    seats = _get(cfg, "flights.commuter.seats")
    _require(isinstance(seats, int) and seats >= 0, "flights.commuter.seats must be a non-negative integer")
    _require(_get(cfg, "flights.commuter.fare") >= 0, "flights.commuter.fare must be >= 0")
    for cabin in CABINS:
        _require(_get(cfg, f"flights.provincial.fare.{cabin}") >= 0, "provincial fares must be >= 0")
    _get(cfg, "flights.provincial.refund_min_lead_min")

    _require(_get(cfg, "finance.checkin_wage_per_hour") >= 0, "finance.checkin_wage_per_hour must be >= 0")
    _get(cfg, "finance.staffing_ratio_limit")

    # Inputs the model's event logic depends on (Person B may add stricter checks).
    lead = _get(cfg, "inputs.provincial_lead_time")
    _require(0 <= lead["lower_min"] < lead["upper_min"],
             "inputs.provincial_lead_time needs 0 <= lower_min < upper_min (arrival at or before departure)")
    _require(_get(cfg, "flights.provincial.first_departure_min") >= lead["upper_min"],
             "flights.provincial.first_departure_min must be >= lead-time upper_min "
             "so that no provincial passenger arrives before t = 0")
    _require(_get(cfg, "flights.provincial.first_departure_min") > 0,
             "the provincial departure at t = 0 is excluded (D12); first_departure_min must be > 0")
    for ptype in ("commuter", "provincial"):
        pmf = _get(cfg, f"inputs.bags_pmf.{ptype}")
        _require(len(pmf) == 3 and all(p >= 0 for p in pmf) and math.isclose(sum(pmf), 1.0, abs_tol=1e-9),
                 f"inputs.bags_pmf.{ptype} must be three probabilities summing to 1")
    _require(_get(cfg, "inputs.commuter_arrival_rate_per_hour") >= 0,
             "inputs.commuter_arrival_rate_per_hour must be >= 0")
