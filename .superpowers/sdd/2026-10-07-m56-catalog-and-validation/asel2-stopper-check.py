"""Offline check of asel2-stopper.unsafe(): fake outputs tree + fake process list. Prints ALL_OK."""
import importlib.util, tempfile, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('stopper', Path(__file__).with_name('asel2-stopper.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
with tempfile.TemporaryDirectory() as tmp:
    S.OUT = Path(tmp)
    root = S.OUT / 'm56_v2_ab_Town12_20261111T000000Z'
    a = root / 'M56-P-L02-S1'; a.mkdir(parents=True); (a / 'a2-bbox.json').write_text('{}')
    ab = [(1, 0, 'python.exe -I -X utf8 native-v2-ab.py rev.json Town12 4')]
    assert S.unsafe(ab) == [], 'raster is safe'
    (a / 'fixture-frozen.json').write_text('{}')
    assert S.unsafe(ab) and 'episode window' in S.unsafe(ab)[0], 'fixture without result is unsafe'
    (a / 'ab-result.json').write_text('{}')
    assert S.unsafe(ab) == [], 'done scene is safe'
    time.sleep(0.05); b = root / 'M56-P-L05-S1'; b.mkdir(); (b / 'a2-bbox.json').write_text('{}'); (b / 'fixture-frozen.json').write_text('{}')
    assert S.unsafe(ab), 'newest scene in its episode window is unsafe'
    assert S.unsafe([(2, 0, 'python native-v6-pair.py x')]), 'pair writer is unsafe'
    assert S.unsafe([]) == [], 'no job is safe'
    assert S.unsafe([(3, 0, 'python native-f-ab.py rev Town12 M56-P-F02 ')]) == [], 'f-ab compile mode is safe'
    assert S.unsafe([(4, 0, 'python native-io-ab.py rev Town12 M56-P-I01 ')]) == [], 'io-ab compile mode is safe'
    S.SINCE[0] = time.time() + 3600
    assert S.unsafe(ab) == [], 'a root older than --since is ignored'
    S.SINCE[0] = 0.
    st = S.status(S.datetime(2000, 1, 1, tzinfo=S.timezone.utc))
    assert st == {f'{root.name}/M56-P-L02-S1': 'DONE', f'{root.name}/M56-P-L05-S1': 'FIXTURE_NO_RESULT'}, st
print('ALL_OK')
