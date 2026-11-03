import numpy as np
import pytest

from airport_sim.rng import RandomStreams, STREAM_NAMES

def test_reproducible_and_independent():
    a = RandomStreams(123, 0).get("bags").random(5)
    b = RandomStreams(123, 0).get("bags").random(5)

    #same seed, same numbers
    assert (a == b).all()
    # different replication                                       
    assert not (a == RandomStreams(123, 1).get("bags").random(5)).all()
    # different stream   
    assert not (a == RandomStreams(123, 0).get("security_service").random(5)).all()

def test_seed_record_reproduces_streams():
    s = RandomStreams(123, 7)
    rec = s.seed_record()
    first = s.get("bags").random(5)

    # keys match the constructor arguments
    rebuilt = RandomStreams(**rec)  
    assert np.array_equal(first, rebuilt.get("bags").random(5))