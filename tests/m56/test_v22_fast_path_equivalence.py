"""v22 speed work (addendum X): the fast paths (incremental trajectory read, per-row reverse-history memo, memoised
_directed_speed and _frame_capability) are the same function as the v21 code path. evidence._V22_FAST=False runs the v21 path.
The closed-loop producer issues every command through the runtime, so identical issued commands and events on both
settings is the equivalence check at the level that matters to the A/B."""
from dataclasses import replace

import pytest

from m56 import evidence
from tests.m56 import f03_cases


@pytest.mark.parametrize('action', ['A', 'B'])
def test_fast_path_issues_the_same_commands_and_events_as_the_v21_path(tmp_path, monkeypatch, action):
    out = {}
    for fast in (False, True):
        monkeypatch.setattr(evidence, '_V22_FAST', fast)
        (tmp_path / str(fast)).mkdir()  # Sources() makes its root without parents
        c = f03_cases.joint_f03_producer(tmp_path / str(fast) / 'sources', action)
        # response_hash is excluded: it digests the per-run source paths, which differ between the two runs
        out[fast] = ({k: replace(v, response_hash='') for k, v in c.issued.items()}, [(e.name, e.frame, e.time) for e in c.events])
    assert out[True][0] == out[False][0]
    assert out[True][1] == out[False][1]
    assert out[True][0]  # not vacuous
