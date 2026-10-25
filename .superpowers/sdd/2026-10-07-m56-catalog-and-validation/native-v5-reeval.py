"""Offline re-evaluation of a native A/B whose CARLA episodes are already sealed (no server, no new episode).

Used when the online A/B process was stopped during its OFFLINE phase (W05 + evaluate_episode), e.g. the 2026-10-25
Town04 C/L A/B stopped after L01's episodes because the pre-bd2fbed evaluation code needed > 3 h. Episodes are rebuilt
with runtime.load_episode (the product's offline reconstruction) and passed to the SAME w05() of native-v2-ab.py.
Validation: run on a scene whose online result exists (M08) and compare verdicts before trusting it.
Run (native venv):  python -I native-v5-reeval.py REVISION.json TOWN SCENE_DIR [SCENE_DIR ...]
Writes <new A/B dir>/<scene>/ab-result.json (create-exclusive); never touches the original A/B directory."""
import json, sys
from pathlib import Path

here = Path(__file__).resolve().parent
revision, town, scene_dirs = sys.argv[1], sys.argv[2], [Path(p) for p in sys.argv[3:]]
sys.argv = [str(here / 'native-v2-ab.py'), revision, town]
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location('ab', here / 'native-v2-ab.py'); ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)
from m56.runtime import load_episode  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402

for sd in scene_dirs:
    scene = sd.name
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    result = {'scene': scene, 'fixture_sha256': ab.sha(sd / 'fixture-frozen.json'), 'episodes': {},
              'reeval': {'source_ab_dir': str(sd), 'method': 'runtime.load_episode + native-v2-ab.w05 (offline)'}}
    for action in 'AB':
        root = sd / 'run' / 'episodes' / scene / action
        ev = load_episode(root)
        if ev is None:
            result['episodes'][action] = {'reason': 'NOT_SEALED_OR_NOT_STARTED'}
            continue
        from dataclasses import replace
        from types import SimpleNamespace
        from m56.runtime import _ref
        # runtime.load_episode maps only its fixed pointer list; the G4 kit seals more '<name>_ref.json' pointers
        # (contact, delivery, motion, *_review). Every sealed pointer file of the episode joins the integrity map.
        store = SimpleNamespace(root=root)
        extra = {f.stem: _ref(store, f.name) for f in sorted(root.glob('*_ref.json'))}
        ev = replace(ev, integrity={**ev.integrity, **extra},
                     source=tuple(dict.fromkeys((*ev.source, *extra.values()))))
        verdict = ab.evaluate_episode(ev, fixture)  # as runtime.run_episode does before returning, then its
        stop = [json.loads(l) for l in (root / 'runner/stop.json').read_text(encoding='utf-8').splitlines() if l.strip()]
        runner_reasons = tuple(stop[-1]['reasons']) if stop else ()  # runner-level reasons (e.g. OUTER_TIMEOUT)
        ev = replace(ev, verdict=replace(verdict, reasons=tuple(dict.fromkeys((*verdict.reasons, *runner_reasons)))))
        result['episodes'][action] = ab.w05(ev, fixture, ab.root / scene / f'w05-{action}')
    (ab.root / scene).mkdir(parents=True, exist_ok=True)
    ab.write_ref(ab.root / scene / 'ab-result.json', result, 'LOCAL_AB_RESULT_REEVAL')
    ab.log(event='AB_REEVAL', **result)
print('DONE', ab.root)
