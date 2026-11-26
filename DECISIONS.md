# Decision Log

Each entry records a modelling or design decision made by the team, the options
that were considered, and why the chosen option was preferred. Entries marked
**[config flag]** are spec ambiguities that a TA might settle differently; the
alternative interpretation is selectable in the config file without code changes.

| ID | Date | Decided by |
|----|------|------------|
| D1–D15 | 2026-10-22 | Person A |
| D16–D22 | 2026-10-22 | Person A (conceptual-model review) |
| D23–D25 | 2026-11-20 | Person A (Phase IV set-up) |
| D4 revised (p = 0.1) | 2026-11-26 | Person A (no TA answer) |

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
- **Options:** (A) applies to every passenger (p = 1); (B) applies to a small share of passengers (p ≈ 0.1); (C) applies to a moderate share (p = 0.25–0.5), with check-in counters as the decision area instead of D23.
- **Chosen (revised 2026-11-26):** B — `inputs.checkin.other_delay_prob: 0.1`. Until 2026-11-26 the baseline used A (p = 1.0); see "D4 resolution" at the end of this log.
- **Rationale:** The spec says "other *problems*/delays", which reads as an exception that affects some passengers, not a step every passenger goes through. The spec gives no probability, so 0.1 (1 passenger in 10) is our assumption and is tested in a sensitivity analysis.

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

## Exploration for the Phase IV decision area (2026-11-20)

Means of 5–10 replications with the final `rng.py`/`variates.py`. These are
exploratory runs to choose the decision area, not reported results.
Reproduce with `run_once.py`/`runner.py` and the overrides shown.

**Offered load (work arriving per hour ÷ capacity) at baseline inputs:**

| Resource | D4 delay for everyone (p = 1) | D4 delay never (p = 0) |
|---|---|---|
| Coach check-in, 3 counters | 1.84 (5.5 counters needed; commuters alone 1.19) | 0.84 |
| Coach check-in, 5 counters (the maximum with 1 business) | 1.10 | 0.51 |
| Coach security, 2 lanes | 1.50 (3.0 lanes needed) | 1.50 |
| Business check-in / security | 0.49 / 0.25 | 0.24 / 0.25 |
| Commuter gate, 40 seats/h | 1.00 | 1.00 |

**What changes `prov_pct_missed` (baseline 90.3%):**

| D4 p | Coach counters / coach lanes | Missed % | Coach check-in wait | Coach security wait | Gate wait | Commuters left behind |
|---|---|---|---|---|---|---|
| 1 | 3 / 2 (baseline) | 90.3 | 2 276 | 4 | 30 | 16 |
| 1 | 5 / 2 | 89.7 | 527 | 1 296 | 36 | 447 |
| 1 | 5 / 4 | 88.4 | 527 | 0.6 | 68 | 3 380 |
| 1 | 5 / 3, `leave_at_departure` | 52.4 | 31 | 3.7 | 108 | 5 392 |
| 0.2 | 5 / 4 | 22.3 | 18 | 7.7 | 128 | 5 891 |
| 0 | 3 / 2 | 83.3 | 39 | 1 664 | 36 | 430 |
| 0 | 3 / 4 | 32.6 | 39 | 2.7 | 132 | 5 798 |
| 0 | 5 / 6 | 5.6 | 12 | 1.1 | 103 | 5 363 |

Observations:

1. **Under D4 p = 1, no check-in or security policy fixes misses.** Coach
   check-in stays overloaded even at the 6-counter maximum, so misses stay
   about 88–90%. Only `leave_at_departure` (D6), which removes missed
   passengers from the queues, brings misses down, to about 52%.
2. **Coach security is the second bottleneck (load 1.5).** It is hidden at
   baseline because check-in lets passengers through slowly. Adding check-in
   counters alone moves the queue to security (security wait rises from 4 to
   1 296 min).
3. **The commuter gate is the third bottleneck.** Once check-in and security
   keep up, gate waits reach 100–130 min and about 5 400–5 900 commuters per
   week are left behind at least once.
4. **Provincial surge.** About 149 provincial passengers arrive within about
   30 minutes, 60–90 minutes before departure, and coach passengers share one
   FIFO queue with commuters. Even with ample capacity, a few percent miss.
5. **The principal KPIs (Person B) use coach *security*.** At baseline the
   coach security wait is 4 min while the coach check-in wait is 2 276 min,
   so KPIs 1 and 3 miss the baseline bottleneck. Raise with B once the
   decision area is chosen.
6. **Security lanes cost nothing in the financial model (D12).** Any
   security-lane alternative wins on profit by construction. Mention this, or
   add a security wage as a config flag.

---

## Phase IV set-up (2026-11-20)

### D23 — Primary decision area: coach security lanes
- **Options:** (A) number/allocation of security lanes; (B) number/allocation of check-in counters; (C) check-in counters and security lanes together.
- **Chosen:** A. The exact alternatives (for example 1B+3C, 1B+4C, and 1B+3C with server sharing) are fixed once D4 is settled.
- **Rationale:** Coach security has offered load 1.5 at baseline under every D4 reading, so it is a structural bottleneck (see the 2026-11-20 exploration above). Check-in is the bottleneck only under the literal D4 reading, and changing both stations at once would leave the study without one primary decision area (spec §8.2).
- **Status:** Unblocked on 2026-11-26 by the D4 resolution (p = 0.1). The exact alternatives are still to be chosen.

### D24 — Alternatives are overlay config files
- **Options:** (A) overlay files with `extends:` that list only the changed keys; (B) full copies of `baseline.yaml`; (C) no files, `--set` overrides in a script.
- **Chosen:** A. Files go in `config/alternatives/`. `config.load_config` follows the `extends:` chain and rejects keys the base file does not have, and the result is validated like any config. `runner.py` is unchanged (`--config config/alternatives/<name>.yaml`), and its `.config.yaml` record names the overlay file.
- **Rationale:** Each alternative shows exactly what differs from the baseline, and a change to the baseline reaches every alternative without hand-syncing copies.

### D25 — Optional security wage **[config flag]**
- **Options:** (A) security lanes are free, as in the spec; (B) add a wage per security lane.
- **Chosen:** A for the baseline: `finance.security_wage_per_hour: 0`. The flag exists because D23 varies security lanes, and with a zero wage any lane alternative wins on profit by construction.
- **Rule when > 0:** Every lane is staffed for the whole horizon (as in D12). The cost is output as `security_staffing_cost` and subtracted from `profit`. It is **not** part of `staffing_ratio`, because the spec's 5% limit is defined for check-in staffing.

### D4 status
- Waiting for the TA's answer (2026-11-20). Phase IV alternatives are on hold until then.

---

## D4 resolution (2026-11-26)

Decided by Person A without a TA answer. Baseline `inputs.checkin.other_delay_prob`
changes from 1.0 to **0.1** (D4 option B).

**Why 0.1.** "Other problems/delays" reads as an exception, not a step every
passenger goes through, and the spec gives no probability. The value is our
assumption. It is reported as one, and the conclusions are tested at other values.

**Where the result changes.** Each passenger's mean check-in time includes 3p
minutes of other delay. With 3 coach counters, coach check-in offered load is

  (40 × (2.35 + 3p) + 119/6 × (2.90 + 3p)) / 180 = 0.84 + 1.00 p,

which reaches 1 at **p ≈ 0.16**. Coach security load is 1.50 for every p.

| p | Coach check-in load | Bottleneck at baseline |
|---|---|---|
| 0 | 0.84 | coach security |
| **0.1** | **0.94** | **coach security** |
| 0.16 | 1.00 | both stations overloaded |
| 0.25 | 1.09 | coach check-in; extra security lanes barely change misses |
| 1 | 1.84 | coach check-in |

**Exploration (5 replications per row, 3 coach counters; not reported results):**

| p | Coach lanes 2 → 3 → 4: % provincial missed | Coach security wait (min) | Commuters left behind |
|---|---|---|---|
| 0.1 | 84 → 69 → 40 | 1 652 → 66 → 2 | 444 → 5 289 → 5 776 |
| 0.25 | 85 → 84 → 84 | 1 319 → 9 → 1 | 438 → 3 398 → 3 573 |
| 0.5 | 87 → 87 → 87 | 558 → 2 → 0.3 | 438 → 1 517 → 1 520 |

**New baseline (10 replications, p = 0.1, mean ± 95% half-width):** coach security
wait 1 632 ± 54 min, coach security utilization 0.998, % provincial missed
83.9 ± 0.5, coach check-in wait 53 ± 2 min, profit $2 764 440 ± $11 778.

**Consequences:**
1. **D23 holds.** Coach security is the baseline bottleneck, so the security-lane
   study is meaningful, and the principal KPIs (coach security wait and
   utilization) now track that bottleneck (2026-11-20 exploration, observation 5).
2. **The recommendation depends on p < 0.16.** Above that, check-in limits
   throughput and extra lanes do little. Phase IV re-runs the baseline and the
   recommended policy at p = 0.05 and p = 0.2, and §12 and the limitations
   section state this condition.
3. **Every earlier result is p = 1.** `results/pilot.csv`, `alt_a.csv` and
   `low.csv` were run with p = 1.0. The pilot has to be re-run, and N chosen
   again (Person B), before the final experiments.
4. **The saved verification traces stay at p = 1.** They check event logic, not
   results, so their commands now pin `inputs.checkin.other_delay_prob=1.0` and
   stay reproducible. With p = 1 the variate code draws no extra uniform, so the
   saved traces are reproduced exactly.
5. The 2026-10-22 open question 1 and the 2026-11-20 exploration above describe
   the p = 1 baseline and are kept as history.
