# Airport-Simulation

Discrete-event simulation of passenger processing at Smiths Falls / Montague
Airport (SYSC 4005, Fall 2026 course project).

> Status: simulation core complete (Phase II, Person A). `airport_sim/rng.py` and
> `airport_sim/variates.py` are **placeholders** that Person B will replace. The
> full reproduction instructions (runner, seeds, experiments) will be added in
> Phase III.

## Setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python scripts/run_once.py                    # one baseline replication, prints all KPIs
.venv/bin/python scripts/run_once.py --rep 3 --set operations.checkin_counters.coach=5
.venv/bin/python scripts/trace.py --start 340 --until 365 --max-lines 50   # event trace around 06:00
.venv/bin/pytest -q                                      # smoke tests
```

From Python (this is what the replication runner calls):

```python
from airport_sim.config import load_config
from airport_sim.model import run_replication

cfg = load_config("config/baseline.yaml", {"operations.security_lanes.coach": 3})
row = run_replication(cfg, replication=0)   # flat dict of KPIs for one replication
```

## Layout

| Path | Contents |
|---|---|
| `config/baseline.yaml` | every model parameter (time in minutes, money in CAD) |
| `airport_sim/` | the simulator (see `docs/software_architecture.md`) |
| `scripts/` | single-run and event-trace scripts |
| `tests/` | pytest suite |
| `docs/conceptual_model.md` | report §4: conceptual model |
| `docs/des_diagram.md` | event graph and process-flow diagrams |
| `docs/software_architecture.md` | report §6: modules and design |
| `DECISIONS.md` | log of modelling decisions (D1–D22) |
