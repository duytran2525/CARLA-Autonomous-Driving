"""A-SEL2 F realized descriptors (docs/m56/F_REALIZED_DESCRIPTORS_20261109.md), offline from sealed raw, product functions only.
Per action A and B:
  readiness frame = first frame the runner's own predicate (m56.runtime._ready) accepts after settle (boundary + SETTLE_S);
  vN_char_r = mean NPC planar speed over the frames in [T - 1 s, T], T = F01_BRAKE_MARKER (F01) / TRIGGER (F02)
              (m56.metrics.detect_events on the sealed raw);
  d0_r      = F01: NPC rear station - EGO front station; F02: EGO rear station - NPC front station; along the frozen
              EGO route (m56.metrics._metric_station of the body vertices) at the readiness frame.
Values are exact Fractions (of the binary64 inputs). Aggregation (mean of A and B) is done by the product (compare_realized).
CLI: python -I native_f_realized.py OUT.json F_AB_SCENE_DIR [...]   (dir = native-f-ab <root>/<scene>)"""
import hashlib, json, sys
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401  (m56 import path)
from m56 import runtime
from m56.geometry import world_vertices
from m56.metrics import _metric_station, detect_events

EVENT = {'F01': 'F01_BRAKE_MARKER', 'F02': 'TRIGGER'}


def _stations(actor, route):
    s = [_metric_station(v, route) for v in world_vertices(actor.body, actor.pose)]
    s = [F(x) for x in s if x is not None]
    return (min(s), max(s)) if len(s) == 8 else None


def readiness_frame(raw, fixture, boundary_time):
    settled = next((i for i, f in enumerate(raw) if f.simtime - boundary_time >= runtime.SETTLE_S), None)
    if settled is None:
        return None
    for i in range(settled + 1, len(raw)):
        if runtime._ready(raw[:i + 1], raw[settled], fixture):
            return raw[i]
    return None


def realized_action(raw, fixture, boundary_time):
    """{'vN_char': Fraction|None, 'd0': Fraction|None, 'event_frame', 'ready_frame'} for one sealed action."""
    mech = fixture.domain.topology['mechanism']
    events = {e.name: e for e in detect_events(tuple(raw), fixture)}
    out = {'vN_char': None, 'd0': None, 'event_frame': None, 'ready_frame': None}
    ev = events.get(EVENT[mech])
    if ev is not None:
        out['event_frame'] = ev.frame
        win = [f for f in raw if ev.time - 1 <= f.simtime <= ev.time]
        sp = [F(sum(float(c) ** 2 for c in a.velocity[:2]) ** .5) for f in win for a in f.actors if a.role == 'NPC']
        if len(sp) == len(win) and sp:
            out['vN_char'] = sum(sp) / len(sp)
    ready = readiness_frame(raw, fixture, boundary_time)
    if ready is not None:
        out['ready_frame'] = ready.frame
        route = fixture.routes['EGO']
        st = {a.role: _stations(a, route) for a in ready.actors}
        if st.get('EGO') and st.get('NPC'):
            gap = st['NPC'][0] - st['EGO'][1] if mech == 'F01' else st['EGO'][0] - st['NPC'][1]
            out['d0'] = gap if gap > 0 else None
    return out


def _ref(path, kind):
    p = Path(path).resolve(); b = p.read_bytes()
    return {'uri': str(p), 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b), 'version': '1', 'method': 'sha256', 'kind': kind}


def scene(d):
    from m56.model import decode_record, load_json
    d = Path(d); fixture = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
    values, detail = {}, {}
    for act in ('A', 'B'):
        root = d / 'run' / 'episodes' / d.name / act
        ep = runtime.load_episode(root)
        if ep is None:
            continue
        pre = root / 'pre_observation_ref.json'
        bt = ep.raw[0].simtime - ep.raw[0].dt  # boundary = the observation before the first recorded frame
        r = realized_action(ep.raw, fixture, bt); detail[act] = {k: str(v) for k, v in r.items()}
        ref = _ref(root / 'trajectory.json', 'NATIVE_SEALED_TRAJECTORY')
        for n in ('vN_char', 'd0'):
            if r[n] is not None:
                values.setdefault(n, {})[act] = (str(r[n]), ref, 1)
        del pre
    return {'scene': d.name, 'category': 'F', 'mechanism': fixture.domain.topology['mechanism'], 'values': values,
            'detail': detail, 'missing': [n for n in ('vN_char', 'd0') if set(values.get(n, {})) != {'A', 'B'}]}


if __name__ == '__main__':
    rows = [scene(x) for x in sys.argv[2:]]
    Path(sys.argv[1]).open('x', encoding='utf-8').write(json.dumps(
        {'spec': 'F_REALIZED_DESCRIPTORS_20261109', 'scenes': rows}, indent=1, default=str))
    for r in rows:
        print(r['scene'], r['detail'], 'missing', r['missing'])
