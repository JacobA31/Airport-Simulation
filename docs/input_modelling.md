# 5. Input Modeling and Random-Variate Generation

All times are in minutes. Every input is a parameter in `config.yaml` (section `inputs`) and is read by `airport_sim/variates.py`. No input was fitted to data, because the project supplies the distributions directly; the modeling work is in choosing truncation limits, defining how components combine, and documenting how each variate is generated.

## 5.1 Summary of input models

| Input | Model | Baseline parameters | Generation method |
|---|---|---|---|
| Commuter arrivals | Poisson process (exponential interarrival times) | 40 passengers/hour; mean gap 1.5 min | Exponential with mean 60/rate |
| Provincial passengers per flight | Binomial, drawn independently per cabin per flight | Business: n = 40, p = 0.75. Coach: n = 140, p = 0.85 | Binomial draw |
| Provincial lead time (minutes before departure) | Truncated normal | Untruncated mean 75, variance 50 (SD ≈ 7.07), limits [0, 180] | Inverse transform (5.3) |
| Checked bags, B | Discrete distribution on {0, 1, 2} | Commuter (0.70, 0.25, 0.05); provincial (0.30, 0.50, 0.20) | Inverse transform on the cumulative pmf |
| Check-in service time | Sum of independent exponentials | Boarding pass mean 2; one mean-1 term per bag; other delays mean 3 | Sum of exponential draws |
| Security service time | Exponential | Mean 3 per passenger | Exponential draw |

## 5.2 Inputs other than the lead time

**Commuter arrivals.** A Poisson process with rate λ = 40/hour is equivalent to independent exponential interarrival times with mean 60/λ = 1.5 minutes. Over the 7-day horizon this gives about 6,720 commuter passengers on average. The rate is a configuration parameter, so the sensitivity analysis changes only one number.

**Provincial passengers per flight.** Each seat is occupied independently with the stated probability, so the number of occupied seats in a cabin is binomial: business ~ Bin(40, 0.75) (mean 30, variance 7.5) and coach ~ Bin(140, 0.85) (mean 119, variance 17.85). Demand is identical across the four daily flight times, as the handout assumes. Each flight's two counts are drawn independently of each other and of every other flight.

**Checked bags.** B is generated independently for each passenger from the pmf for that passenger's type. The cumulative probabilities are (0.70, 0.95, 1.00) for commuters and (0.30, 0.80, 1.00) for provincial passengers. One uniform U is drawn and B is the smallest value whose cumulative probability exceeds U. Expected bags are E[B] = 0.35 (commuter) and 0.90 (provincial).

**Check-in service time.** The total is the sum of three kinds of component:

- boarding-pass processing, Exponential with mean 2;
- bag processing, one independent Exponential with mean 1 for each checked bag (so a passenger with B bags receives a sum of B exponentials);
- other problems/delays, Exponential with mean 3.

The components are assumed mutually independent and independent of the number of bags beyond their dependence on B. The handout gives no probability for "other problems", so the baseline applies this component to every passenger (`other_delay_prob: 1.0`). The mean check-in time is therefore 2 + B + 3, which averages 5.35 minutes for commuters and 5.90 minutes for provincial passengers.

**Security service time.** Exponential with mean 3 minutes, drawn independently for each passenger.

**How exponential and binomial variates are produced.** An exponential variate with mean μ has the inverse-transform form X = −μ ln(1 − U) with U ~ U(0, 1). In the code these are obtained from NumPy's `Generator.exponential` and `Generator.binomial`, which produce the same distributions using NumPy's own algorithms. Their correctness is checked by unit tests (5.5).

## 5.3 Provincial lead time: truncated normal

**Model.** The lead time is X ~ N(μ, σ²) restricted to the interval [a, b], with μ = 75 and σ² = 50 as the *untruncated* parameters, as specified.

**Truncation limits.** The lower limit is a = 0 minutes, since a passenger cannot arrive after the scheduled departure. The upper limit is b = 180 minutes, three hours before departure, which is longer than any plausible advised arrival window. The upper limit must stay well above 90 minutes: a refund requires arriving at least 90 minutes early, so a limit at or below 90 would remove refund-eligible passengers altogether.

**Effect of truncation.** The limits sit at α = (0 − 75)/7.07 ≈ −10.6 and β = (180 − 75)/7.07 ≈ 14.9 standard deviations from the mean, so the truncated distribution is practically identical to the untruncated one (mean ≈ 75, variance ≈ 50). The tail that matters operationally is the fraction arriving more than 90 minutes early, P(X > 90) = 1 − Φ(2.12) ≈ 1.7%, because only these passengers can receive a refund.

**Generation (inverse transform).** Let Φ be the standard normal cdf, α = (a − μ)/σ, β = (b − μ)/σ, and U ~ U(0, 1). Then

X = μ + σ · Φ⁻¹( Φ(α) + U · (Φ(β) − Φ(α)) )

has the required truncated normal distribution. The implementation computes Φ(α) and Φ(β) once, uses `statistics.NormalDist` for Φ and Φ⁻¹, and clamps the result to [a, b] to guard against rounding.

**Why inverse transform rather than acceptance-rejection.** It consumes exactly one uniform per variate, so the number of random numbers drawn from the lead-time stream does not depend on the values drawn. This keeps the random-number streams aligned across experiments that use the same seeds (5.4), and it is exact rather than approximate.

## 5.4 Independence and random-number streams

Each source of randomness uses its own stream: commuter arrivals, provincial seat occupancy, provincial lead time, bag counts, check-in service, and security service. Streams are created per replication from one master seed (`base_seed`) with `SeedSequence(entropy=base_seed, spawn_key=(replication, stream_index))`, as described in the seeding procedure (Section 8). Separate streams make the inputs statistically independent of each other, and allow the baseline and the alternative policies to see the same underlying random numbers for each replication index.

## 5.5 Verification of the generators

`tests/test_variates.py` draws 200,000 variates from each generator with a fixed seed and checks that the sample mean is within four standard errors of the theoretical mean:

| Generator | Theoretical mean |
|---|---|
| Commuter interarrival time | 1.5 min |
| Provincial occupied seats | 30 (business), 119 (coach) |
| Checked bags | 0.35 (commuter), 0.90 (provincial) |
| Check-in time for B = 0, 1, 2 bags | 5, 6, 7 min |
| Security time | 3 min |
| Truncated-normal lead time | Closed-form truncated mean (≈ 75) |

The lead-time test also confirms that every variate lies in [0, 180] and that the fraction above 90 minutes matches the theoretical value (about 1.7%). A rate of zero commuter arrivals returns an infinite interarrival time, used in the extreme-condition test.

## 5.6 Limitation of the truncated-normal assumption and an alternative

**Limitation.** A normal distribution with a standard deviation of about 7 minutes is symmetric and thin-tailed, so nearly all provincial passengers arrive within about 20 minutes of the 75-minute mean. Real arrival behavior is usually right-skewed, with a minority of passengers arriving very early, and it varies by cabin and time of day. Because refunds depend directly on the tail beyond 90 minutes, this assumption may understate the number of refund-eligible passengers, and a symmetric spread also cannot represent the late arrivals that cause most missed flights. The truncation limits themselves have almost no effect, so the limitation is the shape of the distribution rather than the truncation.

**Alternative.** A gamma distribution with the same mean and variance (shape k = μ²/σ² = 112.5, scale θ = σ²/μ ≈ 0.667) is mildly right-skewed (skewness 2/√k ≈ 0.19) and has a slightly heavier upper tail, making it a cheap robustness check: only `provincial_lead_time()` changes. A stronger alternative, if observed arrival times were available, is an empirical distribution (sampling directly from the data or a fitted mixture of "early" and "typical" arrivals). Real arrival data are not provided with this project, so the normal model is retained for all reported experiments and the limitation is stated in Section 14.

## 5.7 Assumptions recorded for this section

- Demand is identical across the four provincial flight times.
- Check-in components are independent exponentials; the "other delays" component applies to every passenger.
- Bag counts are independent across passengers and depend only on passenger type.
- Provincial lead times are independent across passengers and truncated to [0, 180] minutes.
- All input parameters are fixed by the project handout; none was estimated from data.