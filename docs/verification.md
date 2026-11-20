# 7. Verification and Model Credibility

Verification checks that the code implements the conceptual model (§4).
Credibility checks (§7.2) check that the model's behavior is reasonable. Real
operational data for SFMA are not provided, so the model cannot be validated
empirically. Every check here compares the model with the specification, with
hand calculations, or with its own internal consistency.

All evidence is reproducible: `.venv/bin/pytest -q` runs every automated check,
and the commands that produced each trace are at the top of the trace files.

## 7.1 Verification

Person A covers the techniques in 7.1.1–7.1.4. The deterministic hand-calculable
test and the extreme-condition tests are Person B's Phase III items (7.1.5).

### 7.1.1 Event traces for a small number of passengers

`scripts/trace.py` prints one line per event: the clock, the event type, the
passenger and what happened to them, and then the state after the event (queue
lengths and busy servers at check-in and security, and commuters at the gate).
`--pax-table N` adds each passenger's timeline (arrival, service start and end
times, service times S1 and S2, boarding time and final status).

**Trace 1: the first 12 commuters (baseline, replication 0, t ≤ 31 min).**
File: [`verification/trace_commuters.txt`](verification/trace_commuters.txt).
Hand checks against the timeline:

| Check | Evidence |
|---|---|
| Service end = start + service time | Pax 8: check-in 13.263 + 3.171 = 16.434; security 16.863 + 5.875 = 22.738 |
| A passenger waits only when every eligible server is busy | Pax 7 arrives at 9.156 with all 3 coach counters busy (`busy 0/1 3/3`) and joins the queue. Pax 1–6 arrive to an idle counter and start at once (arrive = ci_start) |
| FIFO at check-in | Freed counters take pax 7, 8, 9, 10, 11, 12 in arrival order (`next pax …` in the event lines) |
| Security queue when both coach lanes are busy | Pax 8 finishes check-in at 16.434 with both lanes busy and starts security at 16.863, when pax 4's screening ends |
| Commuter gate and departure | 14 commuters are at the gate at 00:30. The flight boards all 14 (`boarded 14, left behind 0`) and the gate count drops to 0 |
| Business server stays idle under strict dedication (D7) | Business counter and lane show `0/1` throughout while coach passengers queue |

**Trace 2: provincial passengers of the 06:00 flight (1-day horizon, 2 business / 8 coach seats, commuters at 40/h).**
File: [`verification/trace_provincial.txt`](verification/trace_provincial.txt).
Shrinking the flight to about ten passengers keeps the trace short while the
commuter traffic still creates realistic queues. Hand checks:

| Check | Evidence |
|---|---|
| Arrival time = departure − lead time | Pax 191: 360 − 84.347 = 275.653 |
| Business passengers use their own counter and lane | Pax 205 (business) is served at once on the business counter and lane and is through security at 297.348 |
| Catch rule: security must finish at or before D | Pax 205 finishes at 297.348 ≤ 360 and boards at 360.000. Pax 191 finishes security at 360.217, 13 s after the departure, and is marked missed (`left (missed)`) |
| Missed passengers are counted at the departure (D16) | The departure line reads `booked 9, caught 1, missed 8`. Eight coach passengers are still in check-in or security at 06:00 |
| Missed passengers continue and then leave (D6, `continue`) | Each missed passenger completes security after 06:00 and the event line shows `-> left` |
| Refund rule (lead ≥ 90 min) | Pax 442 (flight 2) arrived 90.051 min early, missed the flight, and is `refunded`. Pax 191 (lead 84.3) missed without a refund |
| Separate random streams | Rerunning with `inputs.commuter_arrival_rate_per_hour=0` gives the same ten lead times (only provincial passengers draw from the lead-time stream), and then all ten catch the flight. Bags and service times differ because commuters also draw from those streams. Under a policy change the arrival sequence is unchanged, so every passenger keeps the same draws |

Trace 2 also shows the baseline's main service problem. With only commuters in
the building, 36 coach passengers are already waiting at check-in by 04:35, so
provincial coach passengers queue for about 75 minutes before check-in starts.

### 7.1.2 Passenger conservation and counting checks

Every passenger who arrives is boarded, has left the airport, or is still in
the system at T. Each replication's output contains the counts needed to check
this, and `airport_sim/checks.py` tests these identities:

| Identity | Meaning |
|---|---|
| `comm_arrived = comm_boarded + comm_in_system_end` | Commuters never leave without flying |
| `prov_booked = prov_arrived` | Every booked provincial passenger arrives before their departure |
| `prov_booked = prov_caught + prov_missed` | Every provincial passenger's outcome is decided at their departure |
| `prov_missed = prov_missed_left + prov_in_system_end` | Missed passengers have left or are still being processed |
| `pax_in_system_end = comm_in_system_end + prov_in_system_end` | End-of-run split by type |
| `pax_in_system_end = Σ end_*` | Passengers in the system at T = check-in queues + counters + security queues + lanes + gate |
| `security_completed ≤ checkin_completed` | Nobody reaches security without check-in (when zero-bag commuters do not skip check-in) |

The checks run in two places:

- **In the tests**, after every model run. `tests/helpers.check_conservation`
  also confirms that the counts agree with the individual passenger records.
- **On saved experiment output**, with `scripts/check_conservation.py results/*.csv`.
  On 2026-11-20 every model-output file passed: `pilot.csv` 10/10,
  `alt_a.csv` 30/30, `low.csv` 30/30 replications.

`tests/test_verification.py::test_checker_detects_broken_identities` changes one
count in a valid row and confirms that the checker reports it, so a passing
check is meaningful.

### 7.1.3 Queue and resource-state consistency checks

`tests/helpers.checked_run` attaches a checker to the model's trace hook, so the
following hold after **every** event of a full 7-day run:

- Busy servers in each pool are between 0 and the pool's capacity.
- No server is idle while a passenger it is allowed to serve is waiting
  (respecting the server-sharing mode, D7 and D20).
- Each queue is in FIFO order of queue-join time (checked every 100th event).
- Under `leave_at_departure`, no passenger of a departed provincial flight is
  still waiting in a queue (D21).

The model also asserts, during every run, that no event is scheduled in the
past, that a server is free before service starts and busy before it is
released, and that all of a flight's booked passengers have arrived by its
departure.

These checks run on five baseline replications (`test_verification.py`) and on
eight flag combinations (`test_model_smoke.py`): baseline, both server-sharing
modes, `leave_at_departure`, zero-bag commuters skipping check-in, no commuters,
high capacity, and a gate bottleneck.

### 7.1.4 Automated tests and structured code review

Besides the checks above, the test suite (`.venv/bin/pytest -q`) covers:

| Test (file) | What it shows |
|---|---|
| `test_security_end_exactly_at_departure_catches_flight` (smoke) | Fixed times put security completion exactly at D, and the passenger catches the flight. This verifies the simultaneous-event rule (D9) |
| `test_security_end_just_after_departure_misses_without_refund` (smoke) | 0.001 min later the passenger misses, without a refund (lead 75 < 90) |
| `test_missed_after_arriving_90_min_early_is_refunded` (smoke) | Lead exactly 90 min and a miss → refund. All 8 passengers are refunded ($6,000) |
| `test_commuter_gate_capacity_and_fifo` (smoke) | One commuter per minute with 1-min services: the first flight boards the 28 at the gate, later flights board 40, and boarding is FIFO |
| `test_finance_identities`, `test_refund_rule` (smoke) | Every financial output equals its hand formula (D13) |
| `test_same_seed_reproduces_and_replications_differ` (smoke) | Same seed → identical output; different replication → different output |
| `test_common_random_numbers_across_policies` (verification) | Under more capacity, server sharing, or `leave_at_departure`, every passenger has the same arrival time, bags, service times and lead time as at baseline. This is what makes paired comparisons of alternatives valid |
| `test_rng.py`, `test_variates.py` (Person B) | Streams are reproducible and independent; each variate matches its theoretical mean |

Structured code review: each event routine in `model.py` was compared line by
line with its node in the event graph (`docs/des_diagram.md`) and the event
logic of §4.5.

### 7.1.5 Deterministic and extreme-condition tests (Person B)

*To be written by Person B (Phase III).* Existing tests that B may reuse or
extend: `FixedVariates` in `tests/helpers.py` (fixed service times, a handful of
scheduled passengers) and `test_zero_arrivals_extreme_case` (no arrivals:
nothing in the system, zero utilization, flights still operate empty).

## 7.2 Model credibility (Person B)

*To be written by Person B (Phase III): M/M/c comparison for security under
steady commuter load, and qualitative behavior as capacity rises.* State the
limitation that real operational data are not provided.
