"""v5 erratum 4 (c49d79d, approved by Duy 2026-10-25): the NPC route/plan ends before the first post-destination curve
whose reference lateral acceleration vN^2 * kappa exceeds 2.5 m/s^2 (kappa as the kit measures it)."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
p = 'native-v2-prepare.py'; s = open(p, encoding='utf-8').read()
old = """    rows['NPC'] = (r[k:], [x - arc_n[k] for x in arc_n[k:]]); exit_idx['NPC'] -= k
    cont2 = write_ref(root / c.id / 'routes-v2.json', {k_: v[0] for k_, v in rows.items()}, 'NATIVE_ROUTE')"""
new = """    rows['NPC'] = (r[k:], [x - arc_n[k] for x in arc_n[k:]]); exit_idx['NPC'] -= k
    end = npc_route_end(rows['NPC'], exit_idx['NPC'], vN, region if c.category == 'M' else None)
    out['npc_route_end_e4'] = end
    if end.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=end['reason'])
        return finish(c, out)
    if end.get('cut_index') is not None:
        r4, a4 = rows['NPC']; rows['NPC'] = (r4[:end['cut_index'] + 1], a4[:end['cut_index'] + 1])
    cont2 = write_ref(root / c.id / 'routes-v2.json', {k_: v[0] for k_, v in rows.items()}, 'NATIVE_ROUTE')"""
assert old in s; s = s.replace(old, new)
old = """def min_station(actor, route):"""
new = """def npc_route_end(rows_arc, exit_index, vN, region=None, budget=2.5, window=10., margin=1.):
    \"\"\"v5 erratum 4: s* = first station after the NPC destination with vN^2 * kappa > budget (kappa = |dyaw| over the
    neighbouring rows, as native_v2_kit.Kit.kappa); the route ends at s* - window - margin, which must be >= destination
    + 5 m, else NPC_ROUTE_CURVATURE. Destination = junction exit + 5 m (M: also >= transition-box exit + 5 m).\"\"\"
    rows, arc = rows_arc
    a = [float(x) for x in arc]
    dest = a[exit_index] + 5.
    if region is not None:
        from m56.geometry import _derive_box_sections
        from native_v2_common import directed
        secs = _derive_box_sections(directed(rows, arc, 'e4', 'e4', '0/-1', (), F(str(round(dest, 3)))), region)
        if not hasattr(secs, 'reasons'):
            dest = max(dest, float(secs[1].route_station) + 5.)
    v2 = float(vN) ** 2
    first = None
    for i in range(1, len(rows) - 1):
        if a[i] <= dest:
            continue
        kap = abs(math.radians((rows[i + 1]['yaw'] - rows[i - 1]['yaw'] + 180) % 360 - 180)) / (a[i + 1] - a[i - 1])
        if v2 * kap > budget:
            first = a[i]; break
    if first is None:
        return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': None, 'cut_index': None}
    s_end = first - window - margin
    if s_end < dest + 5.:
        return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': first, 'reason': 'NPC_ROUTE_CURVATURE'}
    cut = max(i for i, x in enumerate(a) if x <= s_end)
    return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': first, 'route_end_m': a[cut], 'cut_index': cut}


def min_station(actor, route):"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
