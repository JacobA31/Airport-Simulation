"""Random-number streams.

Definitions:
- base seed: what controls the randomness in the study and allows for replications
- replication: the independent run
- i: the stream index that indicates which service is being randomized (arrivals, baggage, security)
- seed sequenece: A function that will return a high-quality starting state for an input
- spawn key: the stream you want based on the base seed

Seeding Procedure:
1. Choose one master seed - base_seed is a single non-negative integer (for example 12345) stored in config.yaml. It is the only seed a user supplies.
2. Index the replications. Replication r runs for r = 0, 1, ..., N-1. The pilot uses r = 0..9 or more. The final experiments use r = 0..N-1.
3. Index the streams. Each source of randomness has a fixed position i in STREAM_NAMES:
    -   0 commuter_arrivals
    -   1 provincial_load
    -   2 provincial_lead_time
    -   3 bags
    -   4 checkin_service
    -   5 security_service
4. Build one seed sequence per (replication, stream). For each pair, create SeedSequence(entropy=base_seed, spawn_key=(r, i)). NumPy hashes the entropy and spawn key together into a high-quality internal state.
5. Create the generator and wrap that sequence in Generator(PCG64(...)). Each stream gets its own generator, which the model reads from through RandomStreams.get(name).
6. Use the streams consistently as each source of randomness draws only from its own stream. Because the streams are separate, changing how one source is used does not change the numbers another source receives.
7. Write base_seed and r to the replication-level CSV
"""

from __future__ import annotations

import numpy as np
from numpy.random import Generator, PCG64, SeedSequence

STREAM_NAMES = (
    "commuter_arrivals",
    "provincial_load",
    "provincial_lead_time",
    "bags",
    "checkin_service",
    "security_service",
)


class RandomStreams:
    def __init__(self, base_seed: int, replication: int) -> None:
        if base_seed < 0 or replication < 0:
            raise ValueError("base_seed and replication must be non-negative integers")
        self.base_seed = int(base_seed)
        self.replication = int(replication)
        self._gens: dict[str, Generator] = {
            name: Generator(
                PCG64(SeedSequence(entropy=self.base_seed, spawn_key=(self.replication, i)))
            )
            for i, name in enumerate(STREAM_NAMES)
        }

    def get(self, name: str) -> Generator:
        """Return the (persistent) generator for this stream."""
        try:
            return self._gens[name]
        except KeyError:
            raise KeyError(f"Unknown stream {name!r}; valid names: {STREAM_NAMES}") from None

    def seed_record(self) -> dict:
        """What to log per replication so the run can be reproduced."""
        return {"base_seed": self.base_seed, "replication": self.replication}
