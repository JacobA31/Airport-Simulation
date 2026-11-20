"""Passenger-conservation identities on one replication's KPI row (verification, report §7.1).

These use only the columns that ``run_replication`` returns, so they can be
checked on a live result dict or on every row of a saved replication CSV
(``scripts/check_conservation.py``). The stronger per-event queue/resource
assertions need the model object and live in ``tests/helpers.py``.
"""

from __future__ import annotations

END_STATE_COLUMNS = ("end_checkin_waiting", "end_checkin_in_service", "end_security_waiting",
                     "end_security_in_service", "end_gate_commuters")

# Each identity: (description, left-hand side, right-hand side), sides are functions of the row.
IDENTITIES = (
    ("commuters: arrived = boarded + still in system",
     lambda r: r["comm_arrived"], lambda r: r["comm_boarded"] + r["comm_in_system_end"]),
    ("provincial: booked = arrived",
     lambda r: r["prov_booked"], lambda r: r["prov_arrived"]),
    ("provincial: booked = caught + missed",
     lambda r: r["prov_booked"], lambda r: r["prov_caught"] + r["prov_missed"]),
    ("provincial: missed = left the airport + still in system",
     lambda r: r["prov_missed"], lambda r: r["prov_missed_left"] + r["prov_in_system_end"]),
    ("in system at T = commuters + provincial",
     lambda r: r["pax_in_system_end"], lambda r: r["comm_in_system_end"] + r["prov_in_system_end"]),
    ("in system at T = check-in + security queues and servers + gate",
     lambda r: r["pax_in_system_end"], lambda r: sum(r[c] for c in END_STATE_COLUMNS)),
)


def conservation_violations(row: dict, all_use_checkin: bool = True) -> list[str]:
    """Return a description of every identity the row breaks (empty list = all hold).

    ``all_use_checkin`` is False when zero-bag commuters skip check-in (D5 flag);
    only then may security complete more passengers than check-in.
    """
    bad = []
    for desc, lhs, rhs in IDENTITIES:
        a, b = int(lhs(row)), int(rhs(row))
        if a != b:
            bad.append(f"{desc}: {a} != {b}")
    if all_use_checkin and int(row["security_completed"]) > int(row["checkin_completed"]):
        bad.append(f"security completed {row['security_completed']} > "
                   f"check-in completed {row['checkin_completed']}")
    return bad
