# Scope (Report §3)

## In scope

- Passenger flow from entering the terminal through check-in and security to the gate and departure (a passenger boards, or leaves after missing a provincial flight)
- Commuter and provincial services
- Checked-baggage count (affects check-in service time)
- Refund logic
- Revenue, operating cost, check-in staffing cost, refunds, and profit

## Out of scope (conceptual model §4.1)

- Parking and kerbside
- Walking time between stations (zero, D19)
- The boarding process itself
- Baggage handling after check-in
- Aircraft turnaround and crew
- Weather, flight delays, and cancellations
- Rebooking of missed passengers
- Costs other than flight operating cost and check-in wages (security staff are not costed)
- Passenger behavior beyond the stated rules (no balking or reneging at baseline)
- Group travel (every passenger travels alone)
- Validation against real airport data (none is provided)

## Simulation boundaries

- Horizon: 7 days (10,080 min), starting empty at Monday 00:00, no warm-up period
- Operations run 24/7
- Same horizon for the baseline and all alternatives