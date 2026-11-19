"""v20 (PREREG F03 addendum A5): the runner's reverse dispatch (runtime._bounded) must use the consumer's rule
(evidence._phase_integrity: Mapping, not dict). A native frozen fixture decodes phases to mappingproxy, so under v19 the
EGO B reverse kernel was never dispatched (the stock PID drove the car forward). The synthetic F03 producer
re-implemented the dispatch rule instead of calling the runner's, which hid it."""
from fractions import Fraction as F

import pytest


def test_bounded_follows_the_consumer_rule_on_decoded_phases(tmp_path):
    from m56.model import decode_record, encode_record
    from m56.runtime import _bounded
    from tests.m56.f03_cases import f03_fixture
    from tests.m56.source_cases import Sources
    fixture = f03_fixture(Sources(tmp_path / 's')).fixture
    for r in fixture.responses:
        want = (r.actor_role, r.action_id) == ('EGO', 'B')
        assert _bounded(r) is want, (r.actor_role, r.action_id)  # a FrozenResponse already freezes phases to mappingproxy
        d = decode_record('FrozenResponse', encode_record(r))
        assert not isinstance(d.phases, dict)
        assert _bounded(d) is want, (d.actor_role, d.action_id)  # what a native fixture holds


def test_bounded_f06_npc_script_decoded(tmp_path):
    from m56.model import decode_record, encode_record
    from m56.runtime import _bounded
    from tests.m56.reverse_cases import reverse_case
    r = reverse_case(tmp_path / 'npc', mechanism='F06-ALT1', role='NPC').response
    assert _bounded(r) is True and _bounded(decode_record('FrozenResponse', encode_record(r))) is True


def test_f03_b_through_the_runner_dispatch_on_a_decoded_fixture(tmp_path):
    from tests.m56.f03_cases import joint_f03_producer
    c = joint_f03_producer(tmp_path / 'r', 'B', dispatch='runtime')
    ego = [(n, k) for (role, n), k in sorted(c.issued.items(), key=lambda i: i[0][1]) if role == 'EGO']
    causes = []
    for _, k in ego:
        if not causes or causes[-1] != k.cause:
            causes.append(k.cause)
    assert causes == ['HOLD', 'REVERSE', 'STOPPING', 'FORWARD_GEAR', 'FORWARD'], causes
    for _, k in ego:
        if k.cause == 'REVERSE':  # the bounded kernel's own command: manual gear -1, never a stock forward target
            assert (k.kind, k.control.reverse, k.control.manual_gear_shift, k.control.gear) == ('REVERSE', True, True, -1), k
            assert 0 <= k.control.throttle <= .4 and k.control.steer == 0, k
