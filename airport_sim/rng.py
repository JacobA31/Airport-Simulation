"""Random-number streams.

# PLACEHOLDER — Person B replaces this module.
# Temporary stand-in so the model can run. Person B owns the final seeding
# procedure and its documentation (report §5 / §8). Keep the interface (D15):
#
#     RandomStreams(base_seed: int, replication: int)
#     .get(name: str) -> numpy.random.Generator
#
# with one independent stream per name in STREAM_NAMES.
"""

from __future__ import annotations

import numpy as np

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
        # PLACEHOLDER: one generator per stream, seeded with (base_seed, replication, stream index).
        self._gens = {
            name: np.random.default_rng([base_seed, replication, i])
            for i, name in enumerate(STREAM_NAMES)
        }

    def get(self, name: str) -> np.random.Generator:
        return self._gens[name]
