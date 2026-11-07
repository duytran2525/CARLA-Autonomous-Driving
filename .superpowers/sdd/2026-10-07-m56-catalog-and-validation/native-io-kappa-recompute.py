"""Recompute the kit's reference lateral bound on sealed I/O episodes with both formulas (window-max sum vs pointwise).
usage: python -I kappa_recompute.py SCENE_DIR [...]   (run with cwd = the M56 tooling dir, M56_CODE set)"""
import sys
from pathlib import Path
sys.path.insert(0, '.')
import native_v2_common  # noqa: F401  (M56_CODE first on sys.path)
from native_v2_kit import Kit, profile_kappa, active_target
from m56.model import decode_record, load_json
from m56.runtime import load_episode

for sd in map(Path, sys.argv[1:]):
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    kit = Kit.__new__(Kit); kit.fixture = fixture
    for action in ('A', 'B'):
        ev = load_episode(sd / 'run' / 'episodes' / sd.name / action)
        old = new = (-1., ("", -1))
        for b in ev.raw[1:]:
            for y in b.actors:
                if not y.commands:
                    continue
                r = next(r for r in fixture.responses if r.hash == y.commands[0].response_hash)
                v2 = float(active_target(r, y.commands[0].cause)) ** 2
                o, n = v2 * (kit.kappa(y.role, y) + profile_kappa(r, y)), v2 * kit.lateral_kappa(y.role, r, y)
                old, new = max(old, (o, (y.role, b.frame))), max(new, (n, (y.role, b.frame)))
        print(f'{sd.name} {action}: window-max-sum {old[0]:.4f} at {old[1]}; pointwise {new[0]:.4f} at {new[1]}', flush=True)
