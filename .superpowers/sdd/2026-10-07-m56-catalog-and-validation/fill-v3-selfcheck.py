"""Synthetic self-check of fill-v3-generate.chains_v3 / axis_run (no real map, no census): road 1 (100 m) -> junction
10 straight connector road 2 (20 m) -> road 3 (150 m), lanes -1/-2. Expected one maximal chain of 270 m crossing J10,
axis run 150 m. A 3-degree kink in the connector must stop the chain. python -I fill-v3-selfcheck.py"""
import importlib.util, math, xml.etree.ElementTree as ET
from pathlib import Path
s = importlib.util.spec_from_file_location('v3', Path(__file__).parent / 'fill-v3-generate.py'); v3 = importlib.util.module_from_spec(s)
s.loader.exec_module(v3)

LANES = '''<lanes><laneSection s="0"><center><lane id="0" type="none"/></center><right>
 <lane id="-1" type="driving"><link>{l1}</link><width sOffset="0" a="3.5" b="0" c="0" d="0"/><roadMark sOffset="0" type="broken"/></lane>
 <lane id="-2" type="driving"><link>{l2}</link><width sOffset="0" a="3.5" b="0" c="0" d="0"/><roadMark sOffset="0" type="solid"/></lane>
</right></laneSection></lanes>'''


def xodr(kink_deg):
    h2 = math.radians(kink_deg)
    return f'''<OpenDRIVE>
<road id="1" length="100" junction="-1"><link><successor elementType="junction" elementId="10"/></link>
 <planView><geometry s="0" x="0" y="0" hdg="0" length="100"><line/></geometry></planView>{LANES.format(l1='', l2='')}</road>
<road id="2" length="20" junction="10"><link><predecessor elementType="road" elementId="1" contactPoint="end"/>
 <successor elementType="road" elementId="3" contactPoint="start"/></link>
 <planView><geometry s="0" x="100" y="0" hdg="{h2}" length="20"><line/></geometry></planView>
 {LANES.format(l1='<successor id="-1"/>', l2='<successor id="-2"/>')}</road>
<road id="3" length="150" junction="-1"><link><predecessor elementType="junction" elementId="10"/></link>
 <planView><geometry s="0" x="120" y="0" hdg="{h2 * 2}" length="150"><line/></geometry></planView>{LANES.format(l1='', l2='')}</road>
<junction id="10"><connection id="0" incomingRoad="1" connectingRoad="2" contactPoint="start">
 <laneLink from="-1" to="-1"/><laneLink from="-2" to="-2"/></connection></junction>
</OpenDRIVE>'''


def run(kink):
    root = ET.fromstring(xodr(kink))
    v3.v2.trees['T'] = (root, {int(r.get('id')): r for r in root.findall('road')})
    v3.v2.ANCHORS['T'] = []; v3.v2.CURRENT_JUNCTIONS['T'] = set()
    return [c for c in v3.chains_v3('T', set(), set()) if c['travel'] == 'increasing s']


straight = run(0.)
assert len(straight) == 1, straight
c = straight[0]
assert c['junctions_crossed'] == [10] and abs(c['length'] - 270) < 1e-9 and c['roads'] == [1, 3], c
assert abs(c['axis_run_m'] - 150) < 1e-6, c['axis_run_m']
kinked = run(3.)  # 3 deg connector, 6 deg road 3: crossing refused, so road 1 and road 3 stay separate chains
assert sorted(round(x['length']) for x in kinked) == [100, 150] and not any(x['junctions_crossed'] for x in kinked), kinked
print('fill-v3 selfcheck OK')
