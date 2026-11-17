"""native-io-ab-i12.py (io-i-v1.2 + addendum H probe 3, G1/G2/G3) plus addendum N G5 (PREREG_M56_IO_I_ADDENDUM_N_EVENT_ONSET_
20261117.md). Product m56-v16 holds the EGO B lane change until SOURCE_CLEAR_CONFIRMED; the product still blocks a B whose
lane change starts > 4 s after TRIGGER (SOURCE_CLEAR_WAIT_EXCEEDED). G5 measures the product event in probe 3 (action A, same
fixture, same server, own store): probe 3 now runs on past the geometric t_clear until SOURCE_CLEAR_CONFIRMED is seen or
TRIGGER + 4 s; G5 = SOURCE_CLEAR_CONFIRMED - TRIGGER <= 3.5 s else BLOCKED_FIXTURE SOURCE_CLEAR_EVENT_LATE (no A/B, P5 unspent).
G1/G2/G3 unchanged. No file edited. python -I native-io-ab-i16.py REVISION.json TOWN ID --ab   |   --selftest"""
import importlib.util, sys
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
G5_EVENT_S, G5_CAP_S = F(7, 2), F(4)


def make(base):
    class Probe16(base):
        def see(self, frames, events):
            super().see(frames, events)
            if self.trigger is None or not frames:
                return
            late = frames[-1].simtime - self.trigger.time
            if self.stop == 'T_CLEAR_SEEN':  # the i12 rule stops at the geometric clear; addendum N runs on to the event
                self.stop = 'EVENT_CLEAR_SEEN' if self.event_clear is not None else None
            if self.stop is None and late > G5_CAP_S:
                self.stop = 'TRIGGER_PLUS_4_S'

        def gates(self):
            g = super().gates()
            ev = None if self.event_clear is None or self.trigger is None else self.event_clear - self.trigger.time
            if ev is None or ev > G5_EVENT_S:
                g['reasons'].append('SOURCE_CLEAR_EVENT_LATE')
            g.update(stop=self.stop, pass_=None, event_clear_minus_trigger_s=None if ev is None else str(ev))
            g.pop('pass_'); g['pass'] = not g['reasons']; g['limits']['G5_event_s'] = '7/2'
            return g
    return Probe16


def selftest():
    class Base:  # the i12 Probe contract this subclass relies on
        def __init__(self):
            self.trigger = self.clear = self.event_clear = self.stop = None

        def see(self, frames, events):
            if self.clear is not None:
                self.stop = 'T_CLEAR_SEEN'

        def gates(self):
            return {'pass': True, 'reasons': [], 'stop': self.stop, 'limits': {}}
    p = make(Base)(); p.trigger = SimpleNamespace(time=F(10)); fr = lambda t: [SimpleNamespace(simtime=F(t))]
    p.clear = F(12); p.see(fr(12), ()); assert p.stop is None, p.stop          # geometric clear alone no longer stops
    p.event_clear = F(13); p.see(fr(13), ()); assert p.stop == 'EVENT_CLEAR_SEEN'
    assert p.gates()['pass'] and p.gates()['event_clear_minus_trigger_s'] == '3'
    q = make(Base)(); q.trigger = SimpleNamespace(time=F(10)); q.clear = F(12); q.see(fr(F(141, 10)), ())
    assert q.stop == 'TRIGGER_PLUS_4_S' and q.gates()['reasons'] == ['SOURCE_CLEAR_EVENT_LATE'] and not q.gates()['pass']
    r = make(Base)(); r.trigger = SimpleNamespace(time=F(10)); r.clear = F(12); r.event_clear = F(27, 2)
    r.see(fr(F(27, 2)), ()); assert r.stop == 'EVENT_CLEAR_SEEN' and 'SOURCE_CLEAR_EVENT_LATE' not in r.gates()['reasons']
    r.event_clear = F(136, 10); assert 'SOURCE_CLEAR_EVENT_LATE' in r.gates()['reasons']
    print('SELFTEST_OK')


if __name__ == '__main__' and '--selftest' in sys.argv:
    selftest(); raise SystemExit(0)
spec = importlib.util.spec_from_file_location('ioab12', HERE / 'native-io-ab-i12.py')
I12 = importlib.util.module_from_spec(spec); spec.loader.exec_module(I12)
I12.Probe = make(I12.Probe)  # _i12_probe3 builds Probe(fixture) from this module global
if __name__ == '__main__':
    I12.A.main()
