# Decision Log

Each entry records a modelling or design decision made by the team, the options
that were considered, and why the chosen option was preferred. Entries marked
**[config flag]** are spec ambiguities that a TA might settle differently; the
alternative interpretation is selectable in the config file without code changes.

| ID | Date | Decided by |
|----|------|------------|
| D1–D15 | 2026-10-22 | Person A |
| D16–D22 | 2026-10-22 | Person A (conceptual-model review) |

---

### D1 — Simulation engine: hand-written event-scheduling
- **Options:** (A) hand-written future event list (heap ordered by time, priority, sequence number) with one routine per event type; (B) SimPy process-interaction.
- **Chosen:** A.
- **Rationale:** The spec requires a documented, consistent rule for simultaneous events; with our own event list that rule is explicit in the sort key. The event graph maps one-to-one onto the event routines, event traces are trivial to produce, and there is no third-party simulation dependency to explain in an oral demo. Cost: we write our own queue/server/statistics bookkeeping (~500 lines).

### D2 — Config format and repository layout
- **Options:** (A) YAML; (B) TOML; (C) JSON.
- **Chosen:** A — `config/*.yaml`, loaded by `airport_sim/config.py` (PyYAML).
- **Rationale:** Matches the work-split plan (`config.yaml`), allows comments next to each parameter. Layout: `airport_sim/` package, `config/`, `scripts/`, `tests/`, `docs/`. Person A creates the initial config; Person B takes over the `inputs:` section.

### D3 — Environment and version control
- **Chosen:** Local `.venv` (git-ignored) with numpy, PyYAML, pytest. SciPy is not required (`statistics.NormalDist` provides the inverse normal CDF). Work is committed step by step on branch `model-core`; nothing is pushed without the team's go-ahead.

### D4 — "Other problems/delays" check-in component **[config flag]**
- **Options:** (A) applies to every passenger; (B) applies with probability *p*.
- **Chosen:** A — `inputs.checkin.other_delay_prob: 1.0`.
- **Rationale:** The spec gives no probability, so applying it to everyone is the only literal reading. Consequence noted: with this reading the coach check-in counters are overloaded at baseline (offered load ≈ 1.8× capacity, back-of-envelope). Candidate question for the TA.

### D5 — Commuters with zero bags still use check-in **[config flag]**
- **Options:** (A) every passenger goes through check-in; (B) zero-bag commuters go straight to security.
- **Chosen:** A — `operations.commuter_zero_bag_skips_checkin: false`.
- **Rationale:** Commuters hold no reservation and need a boarding pass; the spec routes all passengers through Station 1.

### D6 — Provincial passengers already late while still in the system **[config flag]**
- **Options:** (A) continue through check-in and security, then leave; (B) leave at the departure instant (finishing any service already started).
- **Chosen:** A — `operations.missed_pax_policy: continue`.
- **Rationale:** Literal reading of §2.6 ("a passenger who completes security after departure misses the flight and leaves"). Because the baseline is overloaded this choice materially affects coach waits, so B stays available as `leave_at_departure`.

### D7 — Business/coach server dedication **[config flag]**
- **Options:** (A) strict dedication at both stations; (B) business passengers may use an idle coach server; (C) cross-use in both directions when the other queue is empty.
- **Chosen:** A for the baseline — `operations.checkin_cross_use: none`, `operations.security_cross_use: none`.
- **Rationale:** The spec says "dedicated". Options B/C are kept as flags because they are a plausible Phase IV policy (the business counter is idle most of the time while coach is overloaded).

### D8 — Commuter gate queue discipline
- **Options:** (A) FIFO by gate-arrival (security completion) time; (B) FIFO by airport-arrival time; (C) random boarding.
- **Chosen:** A.
- **Rationale:** Simplest defensible "first come, first boarded" rule at the gate itself.

### D9 — Simultaneous-event ordering rule
- **Options:** (A) fixed type priority; (B) departures first; (C) pure scheduling order.
- **Chosen:** A. Events with equal time are processed in this order: **security completion → check-in completion → passenger arrival → flight departure → end of simulation**; ties within the same priority are processed in the order they were scheduled (FIFO by sequence number).
- **Rationale:** Implements §2.6 "completes security *at or before* the scheduled departure time catches the flight". (B) would contradict that wording; (C) makes outcomes depend on code order.

### D10 — Provincial demand per flight
- **Options:** (A) booked passengers ~ Binomial(40, 0.75) business and Binomial(140, 0.85) coach, independent across flights; (B) fixed at the means (30 and 119).
- **Chosen:** A. Every booked passenger shows up (no no-shows beyond the occupancy model).
- **Rationale:** Literal reading of "the probability that a seat is occupied"; keeps the demand variability the spec describes.

### D11 — Provincial lead-time truncation and generation method
- **Options:** (A) [0, 180] min; (B) [30, 120] min; (C) μ ± 3σ = [53.8, 96.2] min.
- **Chosen:** A — `inputs.provincial_lead_time.lower_min: 0`, `upper_min: 180`. Generation by **inverse transform**: U ~ Uniform(Φ(α), Φ(β)), X = μ + σ Φ⁻¹(U), with α = (a−μ)/σ, β = (b−μ)/σ.
- **Rationale:** 0 = a passenger cannot arrive after departure; 180 = check-in opens three hours before departure. The upper limit must be ≥ 90 min or refunds become impossible. With σ = √50 ≈ 7.07 min both bounds are > 10σ from the mean, so the truncation essentially never binds. Inverse transform is exact and consumes exactly one uniform per variate (keeps streams synchronised across policy alternatives). Final implementation belongs to Person B (`variates.py`).

### D12 — Horizon, flight schedule and staffing hours
- **Options:** (A) 24/7 operation; (B) invented operating hours.
- **Chosen:** A. t = 0 is Monday 00:00 with an empty system; T = 7 × 1440 = 10 080 min.
  - Provincial flights counted: departures in (0, T] → 06:00 day 1 … 00:00 day 8 = **28 flights**. The t = 0 departure is excluded because its passengers would have arrived before the empty start.
  - Commuter flights: 00:30, 01:30, …, 167:30 h = **168 flights**.
  - Commuter arrivals run 24/7; check-in counters are staffed for the whole horizon. Staffing cost = counters × $35 × 168 h.
  - Security staff are not costed (no wage given in the spec).

### D13 — Revenue, refund and cost rules
- **Options:** (A) provincial revenue for all booked passengers at departure, refunds as a separate line, commuter revenue at boarding; (B) commuter revenue at arrival; (C) provincial revenue only for passengers who fly.
- **Chosen:** A.
  - Gross ticket revenue = Σ over departed provincial flights (booked business × $1000 + booked coach × $500) + boarded commuters × $200.
  - Refunds = Σ fare of missed provincial passengers whose lead time (arrival before departure) ≥ 90 min.
  - Net ticket revenue = gross − refunds.
  - Operating cost = every scheduled flight in the horizon, even if empty.
  - Profit = net revenue − operating cost − staffing cost.
  - Staffing ratio = staffing cost ÷ net revenue; constraint met if ≤ 0.05.
- **Rationale:** Provincial tickets are bought in advance; commuters pay to travel, so commuters still waiting at T earn nothing. Both gross and net are output so the ratio denominator can be switched if the TA prefers.

### D14 — KPI names
- **Chosen:** One flat dict per replication (becomes the replication CSV row). Names are listed in `docs/conceptual_model.md` §4.8.

### D15 — RNG / variates interface with Person B
- **Chosen:**
  ```python
  # rng.py
  class RandomStreams:
      def __init__(self, base_seed: int, replication: int): ...
      def get(self, name: str) -> numpy.random.Generator: ...
      # names: commuter_arrivals, provincial_load, provincial_lead_time,
      #        bags, checkin_service, security_service

  # variates.py   (all times in minutes)
  class Variates:
      def __init__(self, inputs_cfg: dict, streams: RandomStreams): ...
      def commuter_interarrival(self) -> float
      def provincial_booked(self, cabin: str) -> int    # "business" | "coach"
      def provincial_lead_time(self) -> float           # minutes before departure
      def bags(self, ptype: str) -> int                 # "commuter" | "provincial"
      def checkin_time(self, bags: int) -> float        # sum of components
      def security_time(self) -> float
  ```
- **Rationale:** The model calls only these six methods and draws each passenger's bags and service times when the passenger is created, so a given passenger is identical across policy alternatives (common random numbers). Tests can inject a deterministic object with the same methods. Person A ships clearly marked placeholders; Person B replaces the file contents without touching the model.

---

## Conceptual-model review (2026-10-22)

These follow from D1–D15 and were confirmed when `docs/conceptual_model.md` was reviewed.

### D16 — A provincial miss is recorded at the departure instant
- At `PROVINCIAL_DEPARTURE`, every booked passenger of that flight who is not yet at the gate is marked missed, and any refund is recorded then.
- **Rationale:** Under D9 (security completions before departures at equal times) this is exactly the spec's rule "completes security after departure ⇒ missed". Every provincial outcome is therefore known by T, because the last counted flight departs at T.

### D17 — Waiting-time means count only passengers whose service started before T
- **Options:** (A) mean over passengers who started service in [0, T]; (B) also include the unfinished waits (T − queue-join time) of passengers still queued at T.
- **Chosen:** A. Passengers still waiting at T are reported through `pax_in_system_end` and the time-average and maximum queue lengths.

### D18 — Provincial bookings are generated at t = 0
- **Rationale:** Seats are reserved in advance, so the booked counts and lead times of all 28 flights exist before the horizon starts.

### D19 — Walking time from check-in to security is zero
- **Rationale:** Extends the spec's "travel time from security to the gate is negligible" to the check-in → security walk.

### D20 — Server-sharing modes serve their own class first
- Under `business_to_coach` / `both`, a passenger tries their own pool first, and a freed server takes its own pool's queue first (table in `docs/conceptual_model.md` §4.3). Off at baseline (D7).

### D21 — `leave_at_departure` lets passengers already in service finish that service
- Passengers *waiting* in a queue leave at the departure instant; passengers *in service* finish the current service and then leave. Off at baseline (D6).

### D22 — Provincial seats and occupancy live in `inputs.provincial_demand`
- **Rationale:** `Variates` receives only the `inputs:` section (D15), and `provincial_booked()` needs the seat counts. The model itself never needs provincial seat counts, because reserved seats cannot overflow.

---

## Open questions (as of 2026-10-22)

Observations come from single smoke runs with the placeholder variates; they are not analysis results.

1. **D4 — "other delays" for every passenger (ask the TA).** With the 3-min delay for everyone, one provincial flight brings about 880 counter-minutes of check-in work within roughly 30 minutes, 60–90 minutes before departure. About 90% of provincial passengers miss at baseline, about 64% still miss with zero commuters, and the 6-counter maximum does not fix it. With `inputs.checkin.other_delay_prob: 0`, coach check-in load falls from about 1.8× to about 0.84× capacity.
2. **D13 — finance barely reacts to missed flights.** Booked provincial seats earn revenue whether or not the passenger flies, and only passengers who arrived at least 90 min early are refunded (about 1.5% of provincial passengers). Profit therefore stays around $2.6M per week even with 90% misses, and the 5% staffing limit is slack (about 0.7%). The trade-off discussion (§12) should say this explicitly.
3. **Commuter gate is critically loaded.** 40 commuters/h meet 40 seats/h. Once upstream capacity is added, gate waits and left-behind counts grow (one run with 1+5 counters and 3+6 lanes: 66 min mean gate wait, 3 232 commuters left behind). This is relevant to the Phase IV choice of decision area.
4. **Non-stationary baseline.** Baseline queues grow all week, so mean waits and queue lengths depend on the 7-day horizon. Confidence intervals across replications remain valid because the horizon is fixed, but the interpretation should mention this.
