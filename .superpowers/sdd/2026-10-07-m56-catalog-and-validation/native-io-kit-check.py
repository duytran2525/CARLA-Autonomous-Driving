"""I/O tooling: synthetic check of Kit.io_paths (x-axis travel, EGO lane y=0, target lane y=+3.5) and profile_kappa. No server."""
import sys
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import native_v2_common  # noqa (M56_CODE on sys.path)
from native_v2_kit import Kit, profile_kappa
from m56.model import ActorFrame, BodyRecord, ControlPacket, SourceRef, Transform6

REF = SourceRef('synthetic://io', 'a' * 64, 1, 'test', 'literal', 'SYNTHETIC_TEST')
BODY = BodyRecord((0., 0., 0.), (0., 0., 0.), (1.85, .9, .75), (), 'vehicle.audi.a2', {}, {}, REF)
box = lambda y0, y1: tuple(product((-100., 400.), (y0, y1), (-1., 3.)))
topo = {'category': 'O', 'action_regions': {'EGO_INITIAL': box(-1.75, 1.75), 'EGO_TARGET': box(1.75, 5.25)},
        'io_axis': (0, 1), 'io_dlc': F(225, 8)}
fixture = SimpleNamespace(domain=SimpleNamespace(topology=topo), routes={'EGO': 'route'}, pair=None)
kit = Kit.__new__(Kit); kit.fixture, kit.fixture_hash, kit.recipes, kit.authority = fixture, 'h' * 64, {}, REF
backend = SimpleNamespace(_raw=lambda *a, **k: REF)
actor = lambda role, x, y: ActorFrame(role, 1 if role == 'EGO' else 2, Transform6(x, y, 0., 0., 0., 0.), (0., 0., 0.), BODY, F(0), {}, (),
                                      ControlPacket(0., 0., 0., False, False, False, 1), None, 1, True, None)


def run(npc_x, npc_y):
    out = kit.io_paths(backend, 7, F(7, 20), (actor('EGO', 100., 0.), actor('NPC', npc_x, npc_y)))
    return out['lane_change_path'].limits['minimum_clearance_m'], out['return_path'].limits['minimum_clearance_m']


lc, rp = run(130., 0.)        # NPC ahead in the initial lane: target corridor clear by 1.75-0.9 = 0.85; return blocked (0)
assert lc == F(85, 100) and rp == 0, (lc, rp)
lc, rp = run(90., 0.)         # NPC behind the EGO rear (98.15) by 98.15-91.85 = 6.3: return clear
assert rp == F(63, 10) and lc == F(6357, 1000), (lc, rp)  # diagonal: sqrt(6.3^2 + 0.85^2)
lc, rp = run(130., 3.5)       # NPC in the target lane ahead inside [EGO rear, front+Dlc+L]: lane change blocked
assert lc == 0, lc
a = SimpleNamespace(profile={'segments': ({'start_arc_m': F(100), 'length_m': F(225, 8), 'start_offset_m': F(0), 'end_offset_m': F(7, 2)},)},
                    phases={})
assert abs(profile_kappa(a, SimpleNamespace(arc=110)) * (75 / 8) ** 2 - 2.2454) < 1e-3
assert profile_kappa(a, SimpleNamespace(arc=200)) == 0
print('KIT IO CHECK PASS')
