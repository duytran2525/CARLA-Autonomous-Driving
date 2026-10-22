"""Native jitter rule (Duy, 2026-10-22, set AFTER seeing a 0.82 mm native station decrease; old rule kept beside it).

A station decrease no larger than the frame pair's reviewed CONTINUOUS_GEOMETRY uncertainty is jitter, not a reverse.
Without a proof the tolerance is zero (the old rule). reverse_jitter_report lists every decrease the old zero-tolerance
rule would have failed but the new rule accepts, so results can be reported under both rules.
"""
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


@pytest.fixture
def proof(monkeypatch):
    import m56.metrics as metrics
    holder = {'uncertainty': F(1, 1000)}
    monkeypatch.setattr(metrics, '_continuous_proof',
                        lambda a, b, h: None if holder['uncertainty'] is None else SimpleNamespace(uncertainty=holder['uncertainty']))
    monkeypatch.setattr(metrics, '_digest', lambda x: 'h')
    return holder


@pytest.mark.parametrize('before,after,uncertainty,reverse', [
    (F(10), F(10) - F(823974609375, 10**15), F(1, 1000), False),  # native 0.82 mm, within 1 mm: jitter
    (F(10), F(10) - F(2, 1000), F(1, 1000), True),                 # 2 mm > 1 mm: a reverse
    (F(10), F(10) - F(1, 10**6), None, True),                      # no proof: zero tolerance, as before
    (F(10), F(10), F(1, 1000), False), (F(10), F(11), None, False)])
def test_reverse_beyond_jitter(proof, before, after, uncertainty, reverse):
    from m56.metrics import _reverse_beyond_jitter
    proof['uncertainty'] = uncertainty
    assert _reverse_beyond_jitter(object(), object(), before, after, SimpleNamespace()) is reverse


def test_first_frame_has_no_pair_so_no_tolerance(proof):
    from m56.metrics import _reverse_beyond_jitter
    assert _reverse_beyond_jitter(None, object(), F(10), F(10) - F(1, 10**6), SimpleNamespace()) is True


def test_jitter_report_lists_what_only_the_old_rule_fails(proof, monkeypatch):
    import m56.metrics as metrics
    from m56.metrics import reverse_jitter_report
    stations = {1: F(10), 2: F(10) - F(8, 10000), 3: F(10) - F(8, 10000) - F(3, 1000)}
    monkeypatch.setattr(metrics, '_metric_station', lambda point, route: stations[point[0]])
    frames = tuple(SimpleNamespace(frame=n, actors=(SimpleNamespace(role='NPC', pose=SimpleNamespace(x=n, y=0, z=0)),))
                   for n in (1, 2, 3))
    fixture = SimpleNamespace(routes={'NPC': 'route'})
    assert reverse_jitter_report(frames, fixture) == (('NPC', 2, F(8, 10000), F(1, 1000)),)  # frame 3 is a real reverse
