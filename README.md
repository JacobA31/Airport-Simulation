# Airport-Simulation

Discrete-event simulation of passenger processing at Smiths Falls / Montague
Airport (SYSC 4005, Fall 2026 course project).

> Status: the simulation core, input models (`rng.py`, `variates.py`), replication
> runner, and statistical analysis are in place. Verification evidence, the pilot
> and final experiments, and the exact numbers used in the report are added as
> Phases III and IV are completed (see "Reproducing the reported experiments").

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`requirements.txt` lists `numpy`, `scipy`, `pandas`, `pyyaml`, and `pytest`.
Replace `.venv/bin/python` with `.venv\Scripts\python` in the commands below on
Windows, or activate the environment and use plain `python`.

## Run

```bash
.venv/bin/python scripts/run_once.py                    # one baseline replication, prints all KPIs
.venv/bin/python scripts/run_once.py --rep 3 --set operations.checkin_counters.coach=5
.venv/bin/python scripts/trace.py --start 340 --until 365 --max-lines 50   # event trace around 06:00
.venv/bin/pytest -q                                      # tests: random streams, variates, model
```

Replication runner and analysis (run from the project root):

```bash
# N independent replications -> replication-level CSV (+ a record of the config file and overrides used)
.venv/bin/python -m airport_sim.runner --reps 10 --out results/pilot.csv

# means, t-based 95% confidence intervals, half-widths, replications needed
.venv/bin/python -m airport_sim.analysis results/pilot.csv --target-rel 0.05
```

Any configuration value can be overridden on the command line without editing
code, for example `--set operations.checkin_counters.coach=4`. The default
replication count is `simulation.replications`; `--reps` overrides it.

From Python (this is what the replication runner calls):

```python
from airport_sim.config import load_config
from airport_sim.model import run_replication

cfg = load_config("config/baseline.yaml", {"operations.security_lanes.coach": 3})
row = run_replication(cfg, replication=0)   # flat dict of KPIs for one replication
```

## Principal KPIs and where they are in the CSV

| KPI | Column |
|---|---|
| Mean security waiting time | `security_wait_mean_coach` |
| % provincial passengers missing their flight | `prov_pct_missed` |
| Security utilization | `util_security_coach` |
| Total profit | `profit` |

`airport_sim/analysis.py` reports these by default. Business-cabin measures and
other columns can be requested with `--kpis`.

## Random numbers and seeding

Every experiment is reproducible from one integer, `simulation.base_seed`
(4005 in `config/baseline.yaml`).

- Each source of randomness has its own stream: commuter arrivals, provincial
  seat occupancy, provincial lead time, bag counts, check-in service, and
  security service (`STREAM_NAMES` in `airport_sim/rng.py`).
- For replication `r` and stream index `i`, the generator is
  `Generator(PCG64(SeedSequence(entropy=base_seed, spawn_key=(r, i))))`.
  NumPy hashes the entropy and spawn key together, so every (replication, stream)
  pair is statistically independent, and replication `r` can be re-run alone.
- Replications use `r = 0, 1, ..., N-1`. The pilot, baseline, alternatives, and
  sensitivity runs all use the same `base_seed`, so replication `r` sees the same
  underlying random numbers in every experiment.
- `base_seed` and `replication` are recorded in every row of the replication-level
  CSV. Add new streams only at the end of `STREAM_NAMES`, since a stream's position
  is part of its seed.

## Reproducing the reported experiments

Fill in the final replication count `N` after the pilot (chosen from the
confidence-interval half-width criterion, and the same for every experiment).

```bash
# 1. Pilot (10 replications), used to choose N
.venv/bin/python -m airport_sim.runner --reps 10 --out results/pilot.csv
.venv/bin/python -m airport_sim.analysis results/pilot.csv --target-rel 0.05

# 2. Baseline with N replications
.venv/bin/python -m airport_sim.runner --reps N --out results/baseline.csv

# 3. Each alternative (same N, same base_seed), e.g.
.venv/bin/python -m airport_sim.runner --reps N --set operations.checkin_counters.coach=4 --out results/alt_a.csv

# 4. Sensitivity: low / baseline / high commuter arrival rate, for the baseline and
#    the recommended policy (add the policy's --set overrides to the same commands)
.venv/bin/python -m airport_sim.runner --reps N --set inputs.commuter_arrival_rate_per_hour=30 --out results/sens_low.csv
.venv/bin/python -m airport_sim.runner --reps N --set inputs.commuter_arrival_rate_per_hour=50 --out results/sens_high.csv

# 5. Summaries and confidence intervals for the principal KPIs
.venv/bin/python -m airport_sim.analysis results/baseline.csv --out results/baseline_summary.csv
```

Each run writes `<name>.csv` (one row per replication, with the seed record) and
`<name>.config.yaml` (the config file, overrides, and replication count used).

## Layout

| Path | Contents |
|---|---|
| `config/baseline.yaml` | every model parameter (time in minutes, money in CAD) |
| `airport_sim/` | the simulator (see `docs/software_architecture.md`) |
| `airport_sim/rng.py` | independent, reproducible random-number streams per replication |
| `airport_sim/variates.py` | random-variate generators for all stochastic inputs |
| `airport_sim/runner.py` | runs N replications and saves the replication-level CSV |
| `airport_sim/analysis.py` | means, t-based 95% CIs, half-widths, replication-count planning, paired differences |
| `scripts/` | single-run and event-trace scripts |
| `tests/` | pytest suite (random streams, variates against theoretical means, model) |
| `results/` | replication-level CSVs, summaries, and the config record for each run |
| `docs/project_definition/` | report §1–3: objectives, scope, KPIs, assumptions log |
| `docs/conceptual_model.md` | report §4: conceptual model |
| `docs/input_modeling.md` | report §5: input models and variate generation |
| `docs/des_diagram.md` | event graph and process-flow diagrams |
| `docs/software_architecture.md` | report §6: modules and design |
| `DECISIONS.md` | log of modelling decisions (D1–D22) |