"""perf 2026-10-25 (8): optional deferred W05 (M56_DEFER_W05=1): the A/B tool hands the sealed episodes of a scene to a
separate native-v5-reeval.py process (validated identical to the online W05 on M08) and moves on to the next scene
while CARLA stays busy. At most 2 deferred evaluations run at once."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
p = 'native-v2-ab.py'; s = open(p, encoding='utf-8').read()
old = """    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    result = {'scene': c.id, 'fixture_sha256': fref.sha256, 'episodes': {}}"""
new = """    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    if DEFER_W05 and isinstance(out, tuple):
        defer_w05(sd)
        log(event='AB_DEFERRED', scene=c.id, scene_dir=str(sd), fixture_sha256=fref.sha256)
        return
    result = {'scene': c.id, 'fixture_sha256': fref.sha256, 'episodes': {}}"""
assert old in s; s = s.replace(old, new)
old = """def w05(ev, fixture, path):"""
new = """import os, subprocess, time  # noqa: E402
DEFER_W05 = os.environ.get('M56_DEFER_W05', '0') == '1'
_DEFERRED = []


def defer_w05(sd):
    \"\"\"Start native-v5-reeval.py on the sealed scene (results into sd itself); keep at most 2 running.\"\"\"
    while sum(p.poll() is None for p in _DEFERRED) >= 2:
        time.sleep(5)
    env = {**os.environ, 'M56_REEVAL_INTO': '1'}
    py = WORK / '.venv-m56-native-v1/Scripts/python.exe'
    logf = open(sd / 'deferred-w05.log', 'w', encoding='utf-8')
    _DEFERRED.append(subprocess.Popen([str(py), '-I', '-X', 'utf8', str(WS / 'native-v5-reeval.py'), str(REVISION), TOWN, str(sd)],
                                      cwd=str(WS), env=env, stdout=logf, stderr=subprocess.STDOUT))


def w05(ev, fixture, path):"""
assert s.count(old) == 1; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'native-v5-reeval.py'; s = open(p, encoding='utf-8').read()
old = """for sd in scene_dirs:
    scene = sd.name"""
new = """INTO = __import__('os').environ.get('M56_REEVAL_INTO', '0') == '1'  # deferred W05: results into the scene dir itself
for sd in scene_dirs:
    scene = sd.name
    dest = sd if INTO else ab.root / scene"""
assert old in s; s = s.replace(old, new)
old = """        result['episodes'][action] = ab.w05(ev, fixture, ab.root / scene / f'w05-{action}')
    (ab.root / scene).mkdir(parents=True, exist_ok=True)
    ab.write_ref(ab.root / scene / 'ab-result.json', result, 'LOCAL_AB_RESULT_REEVAL')"""
new = """        result['episodes'][action] = ab.w05(ev, fixture, dest / f'w05-{action}')
    dest.mkdir(parents=True, exist_ok=True)
    ab.write_ref(dest / 'ab-result.json', result, 'LOCAL_AB_RESULT' if INTO else 'LOCAL_AB_RESULT_REEVAL')"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
