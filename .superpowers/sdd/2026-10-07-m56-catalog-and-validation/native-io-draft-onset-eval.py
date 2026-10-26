"""REPORT-ONLY, NOT A VALID RESULT: pair evaluation of a sealed I/O A/B under a DRAFT noise-tolerant lateral-onset rule
(proposal docs/m56/PROPOSAL_M56_IO_ONSET_NOISE_20261027.md, set AFTER seeing O03 v1.1; principle 6: needs Duy's approval
before it can count). The consumer bytes are not changed: this process patches two functions in memory only.
  frozen rule: from TRIGGER, the FIRST frame whose map offset changes at all decides: change > 2u -> onset, 0 < change <= 2u
               -> LANE_CHANGE_ONSET_UNCERTAIN; on the return, any decrease <= 2u -> RETURN_LATERAL_START_UNCERTAIN.
  draft rule : changes <= 2u (u = the frame's continuous-geometry uncertainty) are treated as noise and skipped.
Output goes to outputs/m56_v6_pair_<utc>/ like native-v6-pair.py, with 'rule': 'DRAFT_ONSET_NOISE (report only)'.
  python -I native-io-draft-onset-eval.py SCENE_DIR
"""
import inspect, runpy, sys, textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401  (M56_CODE first on sys.path)
from m56 import metrics as M


def patched(fn, old, new):
    src = textwrap.dedent(inspect.getsource(fn))
    assert src.count(old) == 1, (fn.__name__, old)
    exec(compile(src.replace(old, new), f'<draft {fn.__name__}>', 'exec'), M.__dict__)


patched(M._lateral_departure, "            return None,'LANE_CHANGE_ONSET_UNCERTAIN'", "            continue")
patched(M._o_return_action, "                unknown.append('RETURN_LATERAL_START_UNCERTAIN')", "                pass")
here = Path(__file__).resolve().parent
sys.argv = [str(here / 'native-v6-pair.py'), *sys.argv[1:]]
g = runpy.run_path(str(here / 'native-v6-pair.py'), run_name='__draft__')
for p in sys.argv[1:]:
    sd = Path(p).resolve()
    out = g['OUT'] / 'draft-onset-noise-report-only'
    g['pair_scene'].__globals__['OUT'] = out
    g['pair_scene'](sd)
    (out / 'DRAFT_RULE_REPORT_ONLY.txt').write_text('DRAFT_ONSET_NOISE: report only, NOT a valid result; the rule was set '
                                                    'after seeing O03 v1.1 and needs Duy approval.\n', encoding='utf-8')
    print('DRAFT_ONSET_NOISE (report only, not valid):', out / sd.name / 'pair-result.json')
