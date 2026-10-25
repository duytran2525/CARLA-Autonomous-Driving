"""v5 erratum 3 (06144be, approved by Duy 2026-10-25): new M scenes use spec 6.2 G with LrefN = NPC connector road/@length."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
p = 'native-v5-revision.py'; s = open(p, encoding='utf-8').read()
old = """                params = {'G': ParameterProposal('G', (F(str(p['GL_m'])),), 'm', why + '; G = GL (fill20 section 3/4)', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),"""
new = """                lref, g = spec_g(s['town'], br['connecting'], F(str(p['vN'])))
                e3 = (e3_ref,)
                params = {'G': ParameterProposal('G', (g,), 'm', why + '; spec 6.2 G0 with LrefN, ceil to 0.50 m (erratum 3, 06144be)', (prereg_ref, fill_ref, *e3), 'PROPOSED_PREREG_NOT_READY'),
                          'LrefN': ParameterProposal('LrefN', (lref,), 'm', 'spec 6.2: NPC connector road/@length (erratum 3)', (prereg_ref, *e3), 'PROPOSED_PREREG_NOT_READY'),"""
assert old in s; s = s.replace(old, new)
old = """def lane(x):
    return f'{x:+d}'"""
new = """def lane(x):
    return f'{x:+d}'


E3 = WORK / 'docs/m56/PREREG_M56_V5_ERRATUM3_M_G_20261025.md'


def spec_g(town, connector, vN, vE=F(4)):
    \"\"\"Spec 6.2: G0 = vE^2/(2 a) + vE tau + vE (LrefN + 4.5 + 0.5)/(2 vN) + 0.5, G = ceil(G0/0.5)*0.5, exact;
    LrefN = road/@length of the NPC (branch) connector, from the pinned XODR.\"\"\"
    import math, xml.etree.ElementTree as ET
    root = ET.parse(f'E:/Carla/CarlaUE4/Content/Carla/Maps/OpenDrive/{town}.xodr').getroot()
    lref = F(next(r.get('length') for r in root.findall('road') if int(r.get('id')) == int(connector)))
    g0 = vE ** 2 / (2 * F(3, 2)) + vE * F(1, 2) + vE * (lref + F(9, 2) + F(1, 2)) / (2 * vN) + F(1, 2)
    return lref, F(math.ceil(g0 * 2), 2)"""
assert old in s; s = s.replace(old, new)
old = """        fill_ref, prereg_ref = cr.st.ref(fill_path, 'M56_SELECTION_RECEIPT'), cr.st.ref(prereg_path, 'PREREGISTRATION')"""
new = """        fill_ref, prereg_ref = cr.st.ref(fill_path, 'M56_SELECTION_RECEIPT'), cr.st.ref(prereg_path, 'PREREGISTRATION')
        e3_ref = cr.st.ref(E3, 'PREREGISTRATION')"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
