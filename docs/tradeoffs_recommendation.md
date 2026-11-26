# 12. Financial and Operational Trade-offs

> **Draft, provisional numbers** from the 10-replication test run (see the note
> at the top of `docs/alternatives.md`). Tables 12.1 and 12.2 are regenerated
> by `scripts/compare_alternatives.py`. §12.6 waits for Person B's sensitivity
> analysis (§11).

The alternatives are compared on each dimension separately. Following spec
§8.3, no weighted score is used; §13 states which trade-offs decide the
recommendation.

## 12.1 Passenger waiting: security against the commuter gate

Every alternative cuts the coach security wait sharply (Table 10.1), from about
27 hours at baseline to under 3 minutes under A3. Coach passengers are mostly
commuters, so this is chiefly a commuter improvement.

The price is paid at the gate. At baseline the security queue holds back about
2,200 commuters at the end of the week. Once security keeps up, those commuters
reach the gate, where the hourly 40-seat flight exactly matches the arrival rate
of 40 commuters per hour (load 1.0). The gate queue grows: the mean gate wait rises
from 36 to 130 minutes, and the number of commuters left behind at least once
rises from about 430 to about 5,700 (A3).

This is a move of the waiting, not an increase in it. A typical commuter under
A3 waits a few minutes at security and about two hours at the gate, against more
than a day at security under the baseline. The left-behind count rises because
the gate, not security, now sets the pace. "Commuters left behind" should
therefore be read together with the security wait, not on its own.

**Business passengers.** Sharing changes business waits slightly in both
directions. Under A1 the business lane is busy 99% of the time with coach
passengers, and business passengers wait 3.0 ± 0.3 minutes longer. Under A3,
business passengers can also use idle coach lanes and wait 2.8 ± 0.6 minutes less.
Because each lane always serves its own queue first (D20), business passengers
never queue behind coach passengers who are waiting.

## 12.2 Missed flights

| Configuration | Provincial missed (%) | Change vs baseline (pts) |
|---|---|---|
| Baseline | 83.9 | — |
| A1 | 83.5 | −0.4 ± 0.5 (not significant) |
| A2 | 68.2 | −15.7 ± 6.6 |
| A3 | 40.9 | −43.0 ± 0.8 |
| Check (1+4) | 39.8 | −44.1 ± 0.9 |

Security-lane policies roughly halve the missed-flight share, but none goes below
about 40%. The remaining misses come from coach check-in during the provincial
arrival surge (§10.4), which no security policy can reach. Getting below 40%
needs a second decision area: more coach check-in counters at the provincial
peaks (up to the six-counter limit), or advising provincial passengers to arrive
earlier. This is outside the scope of this study (§14).

## 12.3 Resource utilization

| Configuration | Coach lanes | Business lane |
|---|---|---|
| Baseline | 0.997 | 0.25 |
| A1 | 0.992 | 0.99 |
| A2 | 0.980 | 0.25 |
| A3 | 0.827 | 0.73 |
| Check (1+4) | 0.739 | 0.25 |

Without sharing, the business lane is idle three quarters of the time while coach
passengers queue for hours. This is the inefficiency that sharing removes. A3 runs
all four lanes at 73–83%: busy, but with enough slack to absorb random variation.
The 1+4 check adds a lane but uses it mostly as idle capacity. Its coach lanes are
26% idle and its business lane is 75% idle, for almost the same passenger
outcome as A3.

## 12.4 Financial performance

**Where the profit gain comes from.** A3 earns $447,390 ± $6,872 more per week than
the baseline:

| Item | Baseline | A3 | Change |
|---|---|---|---|
| Commuter revenue | $897,060 | $1,315,400 | +$418,340 |
| Provincial revenue | $2,507,950 | $2,507,950 | 0 |
| Refunds | $29,050 | $0 | +$29,050 |
| Operating and check-in staffing cost | $611,520 | $611,520 | 0 |
| **Profit** | **$2,764,440** | **$3,211,830** | **+$447,390** |

94% of the gain is commuter revenue. A commuter pays when they board (D13), and
at baseline about 2,200 commuters are still inside the airport at the end of the
week. Because the baseline security queue grows all week, a longer horizon would
make this loss larger still.

**Missed flights cost the airline little.** Provincial tickets are paid for at
booking, so a missed flight costs only a refund, and only for passengers who
arrived at least 90 minutes early (D13). Refunds are therefore at most $29k a
week, even with 84% of provincial passengers missing their flights. The financial
model has no cost for lost goodwill, rebooking or compensation, so profit
understates the value of reducing missed flights. That reduction is argued on
service grounds (§12.2), not on profit.

**Staffing constraint.** Check-in staffing is unchanged in every alternative
($23,520 a week), so the staffing ratio stays far below the 5% limit: 0.70% at
baseline and 0.61% under A3, which has higher revenue. Security staffing is not
part of the ratio (D25).

**Cost of an extra lane (D27).** The spec gives no security wage, so lanes are
free in the model, and any extra lane would win on profit automatically. Instead
of assuming a wage, Table 12.1 gives the wage at which each extra lane stops
paying for itself (profit gain ÷ 168 staffed hours a week):

**Table 12.1: Break-even security wage per extra lane**

| Step | Profit gain ($/week) | Break-even wage ($/h, 95% CI) |
|---|---|---|
| Third coach lane, no sharing (A2 − Baseline) | 430,990 ± 5,435 | 2,565 (2,533 to 2,598) |
| Third coach lane, with sharing (A3 − A1) | 126,260 ± 11,364 | 752 (684 to 819) |
| A3 over Baseline (third lane plus sharing) | 447,390 ± 6,872 | 2,663 (2,622 to 2,704) |
| Fourth coach lane instead of sharing (Check − A3) | 60 ± 97 | 0.36 (−0.22 to 0.93) |

The third coach lane pays for itself at any realistic wage: about 20 times the
$35/h check-in wage, even when sharing is already in place. The fourth lane does
not pay at any positive wage, because its profit gain is not significantly
different from zero.

## 12.5 Robustness to the "other delays" assumption (D4)

The spec gives no probability for the "other problems/delays" check-in component.
The baseline assumes 0.1 (D4). Coach check-in becomes overloaded at about 0.16,
so the comparison was repeated at 0.05 and 0.2.

**Table 12.2: Key results at three values of `other_delay_prob`** (N = 10)

| p | Config | Coach security wait (min) | Coach check-in wait (min) | Missed (%) | Missed vs baseline (pts) | Profit ($/week) |
|---|---|---|---|---|---|---|
| 0.05 | Baseline | 1,640.5 | 44.7 | 83.5 | — | 2,764,280 |
| 0.05 | A3 | 3.7 | 44.7 | 37.5 | −46.0 ± 0.6 | 3,212,950 |
| 0.1 | Baseline | 1,631.6 | 53.5 | 83.9 | — | 2,764,440 |
| 0.1 | A3 | 2.8 | 53.5 | 40.9 | −43.0 ± 0.8 | 3,211,830 |
| 0.2 | Baseline | 1,468.4 | 265.5 | 84.6 | — | 2,764,280 |
| 0.2 | A3 | 2.3 | 265.5 | 81.7 | −2.9 ± 0.8 | 3,144,830 |

(All four configurations at each p are in Table 12.2 of `results/phase4_tables.md`.)

- **Security waits and profit:** the ranking is the same at every p. A3 has the
  lowest coach security wait and the highest profit of the three alternatives,
  and it beats the baseline by $380–450k per week.
- **Missed flights:** the benefit depends on p. Below the tipping point A3 cuts
  missed flights by 43–46 points. At p = 0.2, coach check-in becomes the
  bottleneck (wait 266 minutes) and A3 cuts missed flights by only 2.9 points.

The security recommendation therefore always helps waiting and profit. Its effect
on missed flights depends on check-in keeping up, which in this model means
p ≲ 0.16.

## 12.6 Sensitivity to commuter demand (§11)

*To be added once Person B's §11 results are available:* does A3 remain
reasonable at 30 and 50 commuters per hour? At 50 per hour, coach security load
rises and the commuter gate (40 seats per hour) is overloaded under every
security policy.

---

# 13. Conclusions and Recommendation

> **Draft. The recommendation is to be confirmed by the team.**

**Recommendation: operate 1 business + 3 coach security lanes with lane sharing
(A3).**

The evidence:

1. **It removes the baseline's main bottleneck.** The coach security wait falls
   from about 27 hours to under 3 minutes (−1,629 ± 54 min), and the share of
   provincial passengers missing their flight falls from 84% to 41%
   (−43.0 ± 0.8 points).
2. **It is as good as a fourth lane, with one lane fewer.** Compared with 1+4,
   A3 is within about 1 minute of security wait and 1 point of missed flights,
   and the profit difference is not significant. Sharing uses the business lane,
   which is idle 75% of the time under dedication.
3. **It pays for itself.** Profit rises by $447k per week, mostly because about
   2,100 more commuters board within the week. The third lane would still pay at
   any wage below about $750/h, against $35/h for a check-in agent.
4. **It holds across the D4 assumption** for waits and profit (§12.5).

**Trade-offs the airline accepts with this recommendation:**

- **Commuter gate congestion.** More commuters reach the gate, and the hourly
  40-seat flight cannot carry them all. Commuters left behind at least once rise
  from about 430 to about 5,700 per week. Their total wait still falls, from more
  than a day at security to about two hours at the gate.
- **Provincial misses stay around 40%** because of the coach check-in surge
  before each provincial departure. If check-in "other delays" are more common
  than assumed (p ≳ 0.16), misses stay above 80%.
- **Operational feasibility of sharing.** Security staff must be able to call
  passengers from the other class's queue when their own queue is empty. Business
  passengers keep priority on the business lane.

**Next steps outside this study's decision area:**

1. Commuter capacity: a larger aircraft or extra departures at peak times. The
   gate runs at exactly full load (40 seats/h for 40 arrivals/h).
2. Coach check-in at provincial peaks: open more counters for 90 minutes before
   each provincial departure, or ask passengers to arrive earlier.

These are the conditions under which the recommendation holds. §14 lists the
model limitations behind it.
