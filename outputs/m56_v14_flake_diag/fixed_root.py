"""Discriminating test (v14 BLOCKED_CONTROLLER flake): arm B of the F06 composition on the failing run's exact temp
root (tmpyuq43w6i, 02:53Z 10/11). Prints a traceback for any BLOCKED_CONTROLLER, the observed-149 hash vs the failing
run (98dc07a4...), and the first frame at which the NPC call reads frozen-stop-NPC.json. The root is moved, never deleted."""
import os, sys, shutil, hashlib, pathlib, traceback
from pathlib import Path
sys.path.insert(0, r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v14')
import m56.response as R
SEED = os.environ.get('PYTHONHASHSEED')
ROOT = Path(r'C:\Users\ADMIN\AppData\Local\Temp\tmpyuq43w6i')
KEEP = Path(__file__).resolve().parent / 'runs'
assert not ROOT.exists(), ROOT
ROOT.mkdir()
orig_blocked = R._blocked_response


def spy(frame, state, response, phase, reason):
    if phase == 'BLOCKED_CONTROLLER':
        print('SEED', SEED, 'BLOCKED', response.actor_role, frame.frame, repr(reason), flush=True)
        print(traceback.format_exc()[-3000:], flush=True)
    return orig_blocked(frame, state, response, phase, reason)


R._blocked_response = spy
ctx = {'npc_frame': None}
first_stop_read = []
orig_read = pathlib.Path.read_bytes


def reader(self):
    if (self.name == 'frozen-stop-NPC.json' and ctx['npc_frame'] is not None and not first_stop_read
            and sys._getframe(1).f_code.co_name == '_source_bytes'):
        first_stop_read.append(ctx['npc_frame'])
    return orig_read(self)


pathlib.Path.read_bytes = reader
orig_ri = R.reverse_intent


def ri(frame, state, response, fixture):
    ctx['npc_frame'] = frame.frame if response.actor_role == 'NPC' else None
    try:
        return orig_ri(frame, state, response, fixture)
    finally:
        ctx['npc_frame'] = None


R.reverse_intent = ri
import tests.m56.f06_cases as C
C.reverse_intent = ri
result = 'OK'
try:
    C.joint_f06_producer(ROOT / 'f06', 'B')
except AssertionError as e:
    result = 'ASSERT ' + str(e)[:120]
obs = ROOT / 'f06' / 'observed-149.json'
h = hashlib.sha256(obs.read_bytes()).hexdigest() if obs.exists() else None
print('SEED', SEED, result, '| observed-149', (h or 'MISSING')[:8], 'match' if h and h.startswith('98dc07a4') else 'NO_MATCH',
      '| first NPC frozen-stop read frame', first_stop_read[:1], flush=True)
KEEP.mkdir(exist_ok=True)
shutil.move(str(ROOT), str(KEEP / f'seed{SEED}'))  # moved, not deleted
