# 4. Conceptual Model

This section describes the discrete-event model of passenger processing at
Smiths Falls / Montague Airport (SFMA) as implemented in `airport_sim/`.
Decision IDs (D1–D15) refer to `DECISIONS.md`; config keys refer to
`config/baseline.yaml`. **Units:** time in minutes, money in CAD.

## 4.1 System boundary and scope

The model starts when a passenger enters the terminal and joins check-in, and
ends when the passenger either boards an aircraft or leaves the airport after
missing a provincial flight. Inside the boundary are three stations:

1. **Check-in** (Station 1): separate business and coach queues and counters.
2. **Security** (Station 2): separate business and coach queues and lanes.
3. **Gate and departure** (Station 3): a FIFO waiting pool for commuters, a
   holding area per provincial flight, and scheduled departures.

The model runs for a fixed horizon of T = 7 days = 10 080 min, starting empty
at t = 0 (Monday 00:00), with no warm-up (D12). Operations run 24/7.

Out of scope: parking and kerbside, walking time between stations, the boarding
process itself, baggage handling after check-in, aircraft turnaround, crew,
weather, flight delays or cancellations, rebooking of missed passengers, and
costs other than flight operating cost and check-in wages.

## 4.2 Entities and attributes

**Passenger** (temporary entity; one per traveller, since everyone travels alone).

| Attribute | Meaning | Set when |
|---|---|---|
| `pid` | unique id, in creation order | creation |
| `ptype` | `commuter` or `provincial` | creation |
| `cabin` | `business` or `coach` (commuters are always `coach`) | creation |
| `flight` | provincial only: the booked flight (gives departure time *D*) | creation |
| `lead_time` *L* | provincial only: minutes between arrival and *D* | creation |
| `t_arrive` | arrival time at the terminal | creation |
| `bags` *B* | checked bags, 0/1/2 | creation |
| `checkin_time` *S₁* | check-in service requirement | creation |
| `security_time` *S₂* | security service requirement | creation |
| `t_q1`, `t_s1`, `t_e1` | check-in: join queue, start service, end service | during run |
| `t_q2`, `t_s2`, `t_e2` | security: join queue, start service, end service | during run |
| `t_gate`, `t_board` | arrival at gate, boarding | during run |
| `status` | `checkin_queue`, `checkin_service`, `security_queue`, `security_service`, `gate`, `boarded`, `left` | during run |
| `missed`, `refunded` | provincial outcome flags | at departure of *flight* |
| `times_left_behind` | commuter only: number of full flights that left without them | each commuter departure |

All random attributes (*B*, *S₁*, *S₂*) are drawn **when the passenger is
created**, each from its own random-number stream, so the same passenger has
the same requirements under every operating policy (D15).

**Provincial flight** (temporary entity; one per scheduled departure in (0, T]).
Attributes: departure time *D*, booked business count *n_B*, booked coach count
*n_C*, list of its passengers, list of passengers waiting at the gate,
`departed` flag.

**Commuter flight**: not stored as an entity. Each commuter departure event is
a batch service of capacity `flights.commuter.seats`.

## 4.3 Resources and capacities

| Resource | Baseline capacity | Config key | Serves |
|---|---|---|---|
| Business check-in counter | 1 | `operations.checkin_counters.business` | business passengers |
| Coach check-in counters | 3 | `operations.checkin_counters.coach` | provincial coach and all commuters |
| Counter space (constraint) | ≤ 6 counters in total | `operations.max_checkin_counters` | — |
| Business security lane | 1 | `operations.security_lanes.business` | business passengers |
| Coach security lanes | 2 | `operations.security_lanes.coach` | provincial coach and all commuters |
| Commuter flight seats | 40 per departure | `flights.commuter.seats` | commuters at the gate |
| Provincial flight seats | 40 business, 140 coach | `inputs.provincial_demand.seats` | booked passengers (reserved, never binding) |

Each counter or lane serves one passenger at a time. Servers are identical
within a pool, never fail, take no breaks and are available for the whole horizon.

**Server-sharing rule** (D7; baseline = `none`), set separately for each station
by `operations.checkin_cross_use` and `operations.security_cross_use`:

| Mode | Passenger arrives at the station | A server becomes free |
|---|---|---|
| `none` | uses an idle server of its own cabin's pool, else joins its own queue | takes the head of its own pool's queue |
| `business_to_coach` | business: own pool, else an idle coach server; coach: own pool only | coach server: coach queue first, else business queue; business server: business queue only |
| `both` | own pool first, else an idle server of the other pool | own queue first, else the other queue |

## 4.4 Queues and disciplines

| Queue | Who joins | Discipline | Capacity / behaviour |
|---|---|---|---|
| Check-in business *Q₁ᴮ* | provincial business | FIFO | unlimited; no balking; no reneging at baseline |
| Check-in coach *Q₁ᶜ* | provincial coach and commuters (mixed) | FIFO | unlimited; no balking; no reneging at baseline |
| Security business *Q₂ᴮ* | provincial business | FIFO | unlimited; no balking; no reneging at baseline |
| Security coach *Q₂ᶜ* | provincial coach and commuters (mixed) | FIFO | unlimited; no balking; no reneging at baseline |
| Commuter gate pool *G* | commuters after security | FIFO by gate-arrival time (D8) | unlimited; up to 40 removed at each commuter departure; the rest stay and are "left behind" |
| Provincial gate area (per flight) | provincial passengers who cleared security by *D* | none needed | everyone in it boards at *D* |

Reneging exists only under the non-baseline flag
`operations.missed_pax_policy: leave_at_departure` (D6). In that case, at a
provincial departure, that flight's passengers still *waiting* in a check-in or
security queue are removed, and passengers *in service* leave when their
current service ends.

## 4.5 Events and event logic

The model uses event scheduling with a future event list (FEL) ordered by
(time, priority, sequence number) (D1). Equal-time events are processed in the
fixed priority order below; ties within one priority follow scheduling order
(D9).

| Priority | Event | Scheduled by |
|---|---|---|
| 1 | `SECURITY_END(p, pool)` | a passenger starting security service |
| 2 | `CHECKIN_END(p, pool)` | a passenger starting check-in service |
| 3 | `COMMUTER_ARRIVAL` | INIT, then itself |
| 3 | `PROVINCIAL_ARRIVAL(booking)` | INIT (one per booked passenger) |
| 4 | `COMMUTER_DEPARTURE` | INIT, then itself |
| 4 | `PROVINCIAL_DEPARTURE(flight)` | INIT, then itself |
| 5 | `END` | INIT |

Priority 1 before 4 means a passenger who finishes security exactly at *D*
catches the flight (§2.6, "at or before").

### Initialisation (t = 0)
1. Empty all queues, set all servers idle, set all statistics to zero.
2. Schedule the first `COMMUTER_ARRIVAL` at *a* ~ Exp(mean 60/λ) min, with λ = `inputs.commuter_arrival_rate_per_hour`.
3. Schedule the first `COMMUTER_DEPARTURE` at `flights.commuter.first_departure_min` (30).
4. For each provincial departure *D* = 360, 720, …, ≤ T (28 flights): create the flight; draw *n_B* ~ Bin(40, 0.75) and *n_C* ~ Bin(140, 0.85); for each booked passenger draw *L* and schedule `PROVINCIAL_ARRIVAL` at *D − L*. Bookings exist before the horizon starts, which is why they are generated at t = 0.
5. Schedule the first `PROVINCIAL_DEPARTURE` at `flights.provincial.first_departure_min` (360).
6. Schedule `END` at T.

### Subroutines (not events)
- **JOIN_CHECKIN(p)**: set `t_q1 = t`. If an eligible check-in server is idle (sharing rule, §4.3), START_CHECKIN(p, pool). Otherwise append p to its cabin's check-in queue.
- **START_CHECKIN(p, pool)**: busy[pool] += 1; `t_s1 = t`; record the wait `t_s1 − t_q1`; schedule `CHECKIN_END(p, pool)` at t + *S₁*.
- **JOIN_SECURITY / START_SECURITY**: the same, for security, with *S₂* and `SECURITY_END`.
- **RELEASE(station, pool)**: busy[pool] −= 1; pick the next passenger for that server under the sharing rule; if one exists, remove them from their queue and START them on this pool.

### Event routines

**COMMUTER_ARRIVAL**
1. Create commuter p (cabin = coach); draw *B*, *S₁*, *S₂*.
2. If `commuter_zero_bag_skips_checkin` and *B* = 0, JOIN_SECURITY(p); otherwise JOIN_CHECKIN(p). (The flag is off at baseline, D5.)
3. Draw *a*; if t + *a* < T, schedule the next `COMMUTER_ARRIVAL` at t + *a*.

**PROVINCIAL_ARRIVAL(booking)**
1. Create provincial p from the booking (flight, cabin, *L*); draw *B*, *S₁*, *S₂*.
2. JOIN_CHECKIN(p).

**CHECKIN_END(p, pool)**
1. `t_e1 = t`; RELEASE(check-in, pool).
2. If p is flagged to leave (only under `leave_at_departure`): p leaves the airport. Otherwise: JOIN_SECURITY(p).

**SECURITY_END(p, pool)**
1. `t_e2 = t`; RELEASE(security, pool).
2. Commuter: `t_gate = t`; append p to the end of the gate pool *G*.
3. Provincial, flight not yet departed (t ≤ *D*, guaranteed by priority 1 < 4): `t_gate = t`; add p to the flight's gate area.
4. Provincial, flight already departed: p leaves the airport. (The miss was already recorded at the departure; see below.)

**COMMUTER_DEPARTURE**
1. *k* = min(seats, |*G*|). Remove the first *k* passengers from *G*. For each: `t_board = t`, record the gate wait `t − t_gate`, add one commuter fare to revenue.
2. Every passenger still in *G* was left behind by this flight: increment `comm_left_behind_events`; if it is their first time, also increment `comm_left_behind`; increment their `times_left_behind`.
3. Add the commuter operating cost (the flight departs even if empty).
4. If t + `interval` ≤ T, schedule the next `COMMUTER_DEPARTURE` at t + 60.

**PROVINCIAL_DEPARTURE(flight)**
1. Everyone in the flight's gate area boards (`t_board = t`, counted as caught).
2. Every other passenger booked on the flight has not finished security by *D*, so has **missed** it. Mark them missed. If *L* ≥ `flights.provincial.refund_min_lead_min` (90), record a refund of their fare. Under `continue` (baseline, D6) they keep going and leave at SECURITY_END. Under `leave_at_departure`, those waiting in a queue are removed now and leave, and those in service are flagged to leave when that service ends.
3. Add revenue for all booked seats (*n_B* × business fare + *n_C* × coach fare) and the provincial operating cost (D13).
4. If t + 360 ≤ T, schedule the next `PROVINCIAL_DEPARTURE`.

Deciding the miss at *D* gives exactly the spec's rule (security completion
after *D* ⇒ missed), and it means every provincial outcome is known by T,
because the last flight departs at T.

**END (t = T)**
Close the time-weighted statistics at T, count the passengers still in the
system, and compute the KPIs and the financial summary (§4.8).

The DES diagrams (process-flow view and event graph) are in
[`docs/des_diagram.md`](des_diagram.md).

## 4.6 State variables

| Symbol | Meaning |
|---|---|
| t | simulation clock (min) |
| FEL | future event list |
| *Q₁ᴮ(t)*, *Q₁ᶜ(t)*, *Q₂ᴮ(t)*, *Q₂ᶜ(t)* | contents (and so lengths) of the four station queues |
| busy₁ᴮ(t), busy₁ᶜ(t), busy₂ᴮ(t), busy₂ᶜ(t) | number of busy servers in each pool (0 … capacity) |
| *G(t)* | commuters waiting at the gate (ordered) |
| per provincial flight: `departed`, gate-area list | provincial gate state |
| cumulative counters | arrivals by type and cabin, check-in and security completions, boarded, missed, refunds, left-behind events and distinct passengers, flights flown |
| statistical accumulators | time-weighted areas under each queue-length and busy-server curve, maximum queue lengths, waiting-time sums and counts |
| financial accumulators | gross revenue, refunds, operating cost |

## 4.7 Inputs and decision variables

**Controllable decision variables** (`operations:` and `flights:` sections):

| Variable | Baseline | Config key |
|---|---|---|
| Check-in counters (business / coach) | 1 / 3 (≤ 6 in total) | `operations.checkin_counters` |
| Security lanes (business / coach) | 1 / 2 | `operations.security_lanes` |
| Server sharing at check-in / security | none / none | `operations.checkin_cross_use`, `operations.security_cross_use` |
| Commuter flight seats and interval | 40 seats, every 60 min from 00:30 | `flights.commuter.seats`, `.interval_min`, `.first_departure_min` |

**Uncontrollable inputs** (`inputs:` section, owned by Person B for §5):

| Input | Baseline | Config key |
|---|---|---|
| Commuter arrival rate | 40 /h, Poisson | `inputs.commuter_arrival_rate_per_hour` |
| Provincial seats and occupancy probability | 40 @ 0.75 business, 140 @ 0.85 coach | `inputs.provincial_demand` |
| Lead time before departure | truncated normal, μ = 75, σ² = 50, limits [0, 180] | `inputs.provincial_lead_time` |
| Bags pmf (commuter / provincial) | (0.70, 0.25, 0.05) / (0.30, 0.50, 0.20) | `inputs.bags_pmf` |
| Check-in components | boarding pass Exp(2), Exp(1) per bag, delay Exp(3) with probability 1.0 | `inputs.checkin` |
| Security time | Exp(3) | `inputs.security_mean_min` |

**Fixed parameters**:
- `simulation:`: horizon, base seed
- `flights:`: provincial schedule, fares, operating costs, refund threshold of 90 min
- `finance:`: wage of $35/h, staffing-ratio limit of 0.05
- `operations:`: the scenario flags `missed_pax_policy` and `commuter_zero_bag_skips_checkin`

## 4.8 Performance measures

`run_replication` returns one flat dictionary per replication, which becomes
one row of the replication CSV. The first column is `replication` (the
replication number). Waits are in minutes, utilisation is a fraction in
[0, 1], and money is in CAD.

**Performance measures** (names agreed in D14; spec §5 table):

| Column | Definition |
|---|---|
| `checkin_wait_mean_business`, `checkin_wait_mean_coach` | mean `t_s1 − t_q1` over passengers of that cabin who **started** check-in service in [0, T] (D17) |
| `checkin_q_avg_business`, `checkin_q_avg_coach` | time-average number **waiting** (not in service) in that check-in queue over [0, T] |
| `checkin_q_max_business`, `checkin_q_max_coach` | maximum number waiting in that check-in queue |
| `security_wait_mean_business`, `security_wait_mean_coach` | mean `t_s2 − t_q2` over passengers of that cabin who started security service in [0, T] |
| `security_q_avg_business`, `security_q_avg_coach` | time-average number waiting in that security queue over [0, T] |
| `security_q_max_business`, `security_q_max_coach` | maximum number waiting in that security queue |
| `util_checkin_business`, `util_checkin_coach`, `util_security_business`, `util_security_coach` | ∫busy(t)dt / (capacity × T) for that server pool (`nan` if the pool has no servers) |
| `prov_booked`, `prov_caught`, `prov_missed` | provincial passengers booked on the flights departing in (0, T], those who boarded, those who missed |
| `prov_pct_missed` | 100 × `prov_missed` / `prov_booked` |
| `refund_count`, `refund_value` | refunded passengers and the total refunded ($) |
| `comm_arrived`, `comm_boarded` | commuter arrivals and boardings in [0, T] |
| `comm_gate_wait_mean` | mean `t_board − t_gate` over commuters who boarded |
| `comm_left_behind` | distinct commuters left behind by at least one full flight |
| `comm_left_behind_events` | total left-behind incidents (one commuter can count more than once) |
| `revenue_gross`, `refunds`, `revenue_net` | ticket revenue before refunds, refunds (equal to `refund_value`), and revenue after refunds (D13) |
| `op_cost`, `staffing_cost`, `profit` | flight operating cost, check-in wages over the horizon, and `revenue_net − op_cost − staffing_cost` |
| `staffing_ratio`, `staffing_ok` | `staffing_cost / revenue_net`; `staffing_ok` = (ratio ≤ `finance.staffing_ratio_limit`) |

**Diagnostic columns** (for conservation checks, the finance check and verification):

| Column | Definition |
|---|---|
| `revenue_commuter`, `revenue_provincial` | the two parts of `revenue_gross`: boarded commuters × fare; booked seats on departed provincial flights × fare |
| `pax_in_system_end`, `comm_in_system_end`, `prov_in_system_end` | passengers neither boarded nor departed at T (all, commuters, provincial) |
| `end_checkin_waiting`, `end_checkin_in_service` | passengers waiting in / being served at check-in at T |
| `end_security_waiting`, `end_security_in_service` | the same for security |
| `end_gate_commuters` | commuters waiting at the gate at T |
| `prov_arrived` | provincial arrivals in [0, T]; equals `prov_booked` because every booked passenger arrives before their flight |
| `prov_missed_left` | missed provincial passengers who had left the airport by T (the rest are still in the queues) |
| `checkin_completed`, `security_completed` | services completed at each station in [0, T] |
| `checkin_cross_served`, `security_cross_served` | passengers served by the other class's server pool (always 0 when sharing is off) |
| `comm_gate_q_avg`, `comm_gate_q_max` | time-average and maximum number of commuters waiting at the gate |
| `n_comm_flights`, `n_prov_flights` | departures flown in the horizon (168 and 28 at baseline) |

Conservation identities checked by the tests:
- `comm_arrived = comm_boarded + comm_in_system_end`
- `prov_booked = prov_caught + prov_missed`
- `prov_missed = prov_missed_left + prov_in_system_end`
- `pax_in_system_end` = the sum of the five `end_*` counts

## 4.9 Assumptions

| # | Assumption | Source |
|---|---|---|
| A1 | One airline, one terminal, two services; every passenger travels alone. | spec §2.1 |
| A2 | Commuter arrivals: stationary Poisson process, λ = 40 /h, 24/7. Arrivals stop at T. | spec §2.2, D12 |
| A3 | Provincial bookings are known at t = 0. Booked counts are Binomial per flight and independent across flights, and every booked passenger shows up. | D10 |
| A4 | Provincial lead times are i.i.d. truncated normal (μ = 75, σ² = 50, limits [0, 180]), generated by inverse transform. | D11 |
| A5 | Bags are i.i.d. per passenger from the pmf for the passenger's type. | spec §2.3 |
| A6 | Check-in time = boarding pass + bag processing + other delay, with the components **independent**. Bag processing is the sum of *B* independent Exp(1) terms (placeholder; final form decided by Person B in §5). The 3-min delay applies to every passenger. | spec §2.4, D4 |
| A7 | Security times are i.i.d. Exp(3). | spec §2.5 |
| A8 | Every passenger goes through check-in then security. Business passengers use the business pools and everyone else the coach pools, with strict dedication at baseline. | D5, D7 |
| A9 | Queues are FIFO and unlimited, with no balking and no reneging at baseline. | D6 |
| A10 | Walking times between the entrance, check-in, security and gate are zero. | spec §2.6 (security → gate), extended |
| A11 | A provincial passenger catches the flight iff security finishes at or before *D*. Missed passengers keep being processed, then leave (no rebooking). A refund is paid iff the passenger missed the flight and *L* ≥ 90 min. | spec §2.6, D6, D9 |
| A12 | Commuters never abandon. They board the next departure with a free seat, in FIFO order at the gate. Flights leave on time and fly even when empty. | spec §2.6, D8, D13 |
| A13 | 7-day horizon, empty and idle start, no warm-up. The provincial flight at t = 0 is excluded and the one at t = T is included. | spec §6.1, D12 |
| A14 | Check-in counters are staffed for the whole horizon. Security, gate and other staff costs are not modelled. | D12 |
| A15 | Waiting-time means include only passengers whose service *started* before T. Passengers still waiting at T are reported through `pax_in_system_end` and the queue-length statistics. | D17 |
