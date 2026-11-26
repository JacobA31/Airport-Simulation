# 10. Alternative-Policy Experiments and Comparison

> **Draft, provisional numbers.** All numbers come from a 10-replication test run.
> When Person B fixes the final replication count N, re-run
> `python scripts/run_phase4.py --reps N` and `python scripts/compare_alternatives.py`,
> then replace the numbers below with those in `results/phase4_tables.md`.
> The table numbers in this section match that file.

## 10.1 Decision area and alternatives

The baseline (§9) has one clear bottleneck: the coach security lanes. At baseline
inputs they receive 1.5 times the work they can do (offered load 1.50), their
utilization is 0.997, and their queue grows all week to a mean wait of about
1,630 minutes. Coach check-in keeps up (load 0.94 at `other_delay_prob` = 0.1, D4).
The study therefore has one primary decision area (spec §8.2): **the number and
allocation of security lanes** (D23).

Two levers are varied in a 2 × 2 design (D26):

- **Number of coach lanes:** 2 (baseline) or 3. The business lane stays at 1.
- **Lane sharing** (`operations.security_cross_use: both`): with sharing on, a
  passenger whose own lanes are all busy may use an idle lane of the other
  class. Each lane always serves its own queue first (D20). With sharing off,
  lanes are strictly dedicated, as in the spec (D7).

| Configuration | Business + coach lanes | Sharing | Config file | What it tests |
|---|---|---|---|---|
| Baseline | 1 + 2 | off | `config/baseline.yaml` | — |
| A1 | 1 + 2 | on | `config/alternatives/a1_share.yaml` | reallocating the existing lanes |
| A2 | 1 + 3 | off | `config/alternatives/a2_coach3.yaml` | adding one coach lane |
| A3 | 1 + 3 | on | `config/alternatives/a3_coach3_share.yaml` | both together |
| Check | 1 + 4 | off | `config/alternatives/check_coach4.yaml` | side check: is sharing worth a lane? |

Every other parameter is the baseline value. Each alternative file lists only
what it changes (D24), and a test checks that the files differ from the baseline
only in these two settings.

## 10.2 Experimental conditions

All configurations use the same conditions:

- the same 7-day horizon, empty start, and N replications (spec §6.1–6.2);
- the same `base_seed`, so replication *r* has the same passengers in every
  configuration: the same arrival times, bags, service times and lead times
  (common random numbers, verified by `test_common_random_numbers_across_policies`);
- the same performance measures, with the four principal KPIs reported with
  t-based 95% confidence intervals.

Because replication *r* is matched across configurations, differences are
estimated with **paired** confidence intervals: the CI of the per-replication
difference, using `analysis.paired_difference_ci`. A difference is called
significant when its 95% CI excludes zero. The common random numbers make these
intervals much narrower than independent comparisons. For example, the profit
difference A3 − Baseline has a half-width of $6.9k, while each profit estimate
alone has a half-width of about $12–15k.

## 10.3 Results

**Table 10.1: Principal KPIs** (mean ± 95% half-width, N = 10, provisional)

| Configuration | Coach security wait (min) | Provincial missed (%) | Coach security utilization | Profit ($/week) |
|---|---|---|---|---|
| Baseline (1+2) | 1,631.6 ± 53.9 | 83.9 ± 0.5 | 0.997 ± 0.001 | 2,764,440 ± 11,778 |
| A1 (1+2, sharing) | 435.4 ± 52.8 | 83.5 ± 0.7 | 0.992 ± 0.001 | 3,085,570 ± 9,432 |
| A2 (1+3) | 66.2 ± 19.5 | 68.2 ± 6.9 | 0.980 ± 0.006 | 3,195,430 ± 13,775 |
| **A3 (1+3, sharing)** | **2.8 ± 0.3** | **40.9 ± 1.0** | **0.827 ± 0.004** | **3,211,830 ± 14,570** |
| Check (1+4) | 1.7 ± 0.2 | 39.8 ± 1.1 | 0.739 ± 0.005 | 3,211,890 ± 14,586 |

**Table 10.4: Effect of each change** (paired difference ± 95% half-width; * = significant)

| Change | Coach security wait (min) | Provincial missed (pts) | Profit ($/week) | Commuters left behind | Business security wait (min) |
|---|---|---|---|---|---|
| Sharing on, 2 coach lanes (A1 − Baseline) | −1,196 ± 19* | −0.4 ± 0.5 | +321,130 ± 6,089* | +2,816 ± 108* | +3.0 ± 0.3* |
| One more coach lane, no sharing (A2 − Baseline) | −1,565 ± 44* | −15.7 ± 6.6* | +430,990 ± 5,435* | +4,823 ± 333* | 0.0 |
| Sharing on, 3 coach lanes (A3 − A2) | −63 ± 19* | −27.2 ± 6.6* | +16,400 ± 7,979* | +448 ± 236* | −2.8 ± 0.6* |
| A3 − Baseline | −1,629 ± 54* | −43.0 ± 0.8* | +447,390 ± 6,872* | +5,271 ± 340* | −2.8 ± 0.6* |
| Fourth lane instead of sharing (Check − A3) | −1.1 ± 0.2* | −1.1 ± 0.5* | +60 ± 97 | +8 ± 10 | +2.8 ± 0.6* |

The full tables, including secondary measures (Table 10.2) and every
configuration minus the baseline (Table 10.3), are in `results/phase4_tables.md`.

## 10.4 Interpretation

**Reallocating the existing lanes (A1) helps, but not enough.** The business lane
is idle 75% of the time at baseline (utilization 0.25). Sharing lets coach
passengers use that idle time and cuts the coach security wait by about 1,200
minutes, but coach security is still overloaded (utilization 0.99) and the share
of provincial passengers missing their flight does not change significantly
(−0.4 ± 0.5 points). The business lane becomes almost fully busy (0.99), and
business passengers wait about 3 minutes longer.

**A third coach lane (A2) removes the overload, but only just.** The coach
security work is about 3.0 lanes' worth (offered load 1.5 on 2 lanes), so on 3
lanes the offered load is 1.0: utilization is 0.98 and the system is critically
loaded. Waits fall to about an
hour, but they vary a lot between replications (missed: 68.2 ± 6.9%), as
expected for a queue running at full load.

**A3 combines the two and gives the largest single improvement.** With a third
coach lane, sharing gives the coach passengers the spare business-lane capacity
that A2 leaves unused. This removes the critical loading: coach utilization
falls to 0.83, the mean coach security wait to under 3 minutes, and missed
flights by a further 27 points compared with A2. Business passengers also gain
(−2.8 min), because under sharing they may use an idle coach lane.

**Sharing is worth almost a full lane.** A fourth coach lane instead of sharing
(Check) improves the coach security wait by only 1.1 minutes and the
missed-flight share by 1.1 points, and the profit difference is not significant
(+$60 ± $97). The fourth lane mostly adds idle capacity (coach utilization 0.74)
and leaves the business lane idle again.

**About 40% of provincial passengers still miss their flight under A3 and
Check.** Once security keeps up, the remaining misses happen at coach check-in.
About 150 provincial passengers per flight arrive in roughly 30 minutes, 60–90
minutes before departure (lead time 75 ± 7 min), and join the same FIFO queue as
the commuters. Coach check-in can keep up on average (load 0.94) but not with
this surge. This is outside the security decision area and is discussed in §12
and §14.

**Moving the bottleneck to the commuter gate.** Under the baseline, most
commuters are still in the security queue: only 4,485 of 6,715 arriving commuters
board within the week. Under A3, 6,577 board. More commuters now reach the gate,
where the hourly 40-seat flight matches the arrival rate of 40 per hour exactly.
The gate queue therefore grows, and the number of commuters left behind at least
once rises from about 430 to about 5,700 (mean gate wait 36 → 130 minutes). This
is the main trade-off of every alternative and is discussed in §12.
