# Principal KPIs (Report §2)

Each KPI is computed once per replication over the 7-day horizon (10,080 min). For each, the report gives the mean and a t-based 95% confidence interval across independent replications.

| # | KPI | Category | Definition | CSV column |
|---|---|---|---|---|
| 1 | Mean security waiting time | Waiting time (passenger service) | Mean time in the coach security queue, in minutes, over passengers whose screening started before the end of the horizon (D17). Business-cabin wait is reported as a secondary measure | `security_wait_mean_coach` |
| 2 | % of provincial passengers missing their flight | Service outcome | 100 × `prov_missed` / `prov_booked`: booked provincial passengers marked missed at departure (D16), as a percentage of booked provincial passengers (`docs/conceptual_model.md` §4.8) | `prov_pct_missed` |
| 3 | Utilization of security resources | Resource utilization | Busy time of the coach security lanes ÷ (number of lanes × horizon length) | `util_security_coach` |
| 4 | Total profit | Financial | Net ticket revenue (gross revenue minus refunds) − flight operating cost − check-in staffing cost | `profit` |

## Why this set

It includes a waiting-time measure (1) and a service outcome (2), as required, plus a resource measure (3) and a financial measure (4). The measures are linked: security staffing drives waiting and utilization, waiting drives missed flights, and missed flights drive refunds and profit.

The coach security lanes are used for KPIs 1 and 3 because they carry all commuter traffic and most provincial passengers, and they are where a bottleneck would appear. Business-cabin measures (`security_wait_mean_business`, `util_security_business`) are collected and reported as secondary results.

## Other required measures (collected, not analysed with full CIs)

| Category | CSV columns |
|---|---|
| Check-in | `checkin_wait_mean_*`, `checkin_q_avg_*`, `checkin_q_max_*` |
| Security | `security_wait_mean_*`, `security_q_avg_*`, `security_q_max_*` |
| Resources | `util_checkin_*`, `util_security_*` |
| Provincial service | `prov_caught`, `prov_missed`, `prov_pct_missed`, `refund_count`, `refund_value` |
| Commuter service | `comm_gate_wait_mean`, `comm_left_behind` |
| Financial | `revenue_gross`, `refunds`, `revenue_net`, `op_cost`, `staffing_cost`, `profit` |

(`*` is `business` or `coach`.)

## Related constraint (not a KPI)

Check-in staffing cost should stay within 5% of ticket revenue. The model computes `staffing_ratio` = check-in staffing cost ÷ net ticket revenue over the 7-day horizon (D13), where every check-in counter is staffed for the whole horizon at $35/hour (D12), and `staffing_ok` flags whether the ratio is at most 0.05. Report the mean and CI of `staffing_ratio`, or the fraction of replications with `staffing_ok` true; do not report a mean and CI for the flag itself.