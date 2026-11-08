"""Build and freeze C0 PARTIAL v5: the 31 C0-partial candidates (rebuilt exactly as native-v2-revision.py) + the fill v2
(409911e) / v3 (4a26a66) additions whose recipe the existing builders can complete, then the prepared runtime recipes.

Additions: M02-M08 (junction_recipe, EGO = mainflow at 4 m/s, NPC = branch at vN; G = the registered GL series value)
and F03 (f_recipe, uphill lane per F2-4). Excluded with a recorded reason (never silently): F02 (no F02 recipe builder),
I06/O06 (multi-road corridor through J764: io_recipe supports one road only). The index k is not a physical parameter
(model units m, m/s, s, m/s^2, deg), so it is recorded in the rationale, not as a ParameterProposal (F2-5).
Identity: touching-cross-section-v1 on outputs/m56_site_identity_v5_*.json; touching sites share one site id.
Reviews: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, independent review waived by Duy 2026-10-24; never presented as Duy's own.
Run (main venv):  python -I native-v5-revision.py OUTDIR IDENTITY_V5.json PREPARE_DIR [PREPARE_DIR ...]
"""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import hashlib, importlib.util, json, sys
from collections.abc import Mapping

here = Path(__file__).resolve().parent
sys.path[:0] = [str(here), 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1']
spec = importlib.util.spec_from_file_location('rev2', here / 'native-v2-revision.py'); rev2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rev2)
cr = rev2.cr
from m56.catalog import _digest, _site_digest, freeze_c0, review_sites  # noqa: E402
from m56.model import (ActorRecipe, Candidate, CandidateRevision, IdentityMethod, ParameterProposal, ReviewRecord,  # noqa: E402
                       SiteRecord, encode_record)

WORK = rev2.WORK
FILLS = {'v2': (WORK / 'outputs/m56_fill_v2_20261024T152517Z.json', WORK / 'docs/m56/PREREG_M56_FILL_V2_20261024.md', '409911e'),
         'v3': (WORK / 'outputs/m56_fill_v3_20261024T153441Z.json', WORK / 'docs/m56/PREREG_M56_FILL_V3_20261024.md', '4a26a66')}
EXCLUDE = {'M56-P-F02': 'RECIPE_BUILDER_MISSING: catalog-recipes f_recipe has no F02 builder',
           'M56-P-I06': 'RECIPE_BUILDER_MISSING: io_recipe supports one road; corridor 47 -> J764 -> 48',
           'M56-P-O06': 'RECIPE_BUILDER_MISSING: io_recipe supports one road; corridor 47 -> J764 -> 48'}
REVIEWER = rev2.REVIEWER
TOWNCODE = {'Town04': 'P04', 'Town05': 'P05', 'Town06': 'P06', 'Town07': 'P07',  # A-SEL2 towns below
            'Town01': 'P01', 'Town02': 'P02', 'Town10HD': 'P10', 'Town11': 'P11', 'Town12': 'P12', 'Town13': 'P13', 'Town15': 'P15'}
RUNTIME_PREREGS = [WORK / 'docs/m56' / n for n in ('PREREG_M56_RUNTIME_RECIPE_V2_20261023.md', 'PREREG_M56_V5_CONSUMER_PID_20261024.md',
                                                    'PREREG_M56_V5_ERRATUM1_C3_20261024.md', 'PREREG_M56_V5_ERRATUM2_EGO_PID_20261024.md')]


def lane(x):
    return f'{x:+d}'


E3 = WORK / 'docs/m56/PREREG_M56_V5_ERRATUM3_M_G_20261025.md'


def spec_g(town, connector, vN, vE=F(4)):
    """Spec 6.2: G0 = vE^2/(2 a) + vE tau + vE (LrefN + 4.5 + 0.5)/(2 vN) + 0.5, G = ceil(G0/0.5)*0.5, exact;
    LrefN = road/@length of the NPC (branch) connector, from the pinned XODR."""
    import math, xml.etree.ElementTree as ET
    root = ET.parse(f'E:/Carla/CarlaUE4/Content/Carla/Maps/OpenDrive/{town}.xodr').getroot()
    lref = F(next(r.get('length') for r in root.findall('road') if int(r.get('id')) == int(connector)))
    g0 = vE ** 2 / (2 * F(3, 2)) + vE * F(1, 2) + vE * (lref + F(9, 2) + F(1, 2)) / (2 * vN) + F(1, 2)
    return lref, F(math.ceil(g0 * 2), 2)


def additions(out, decision_ref, xodr, weather, identity_pairs):
    adds, report = [], []
    for tag, (fill_path, prereg_path, commit) in FILLS.items():
        fill_ref, prereg_ref = cr.st.ref(fill_path, 'M56_SELECTION_RECEIPT'), cr.st.ref(prereg_path, 'PREREGISTRATION')
        e3_ref = cr.st.ref(E3, 'PREREGISTRATION')

        def attest(digest, scope, why):
            return ReviewRecord(digest, scope, (fill_ref, prereg_ref), 'CLAUDE_MECHANICAL_ATTESTATION_UNDER_DUY_DELEGATION',
                                '2026-10-24', 'APPROVED', (why,), decision_ref)
        for e in json.loads(fill_path.read_text(encoding='utf-8'))['entries']:
            if e['status'] != 'PROPOSED':
                continue
            if e['id'] in EXCLUDE:
                report.append({'id': e['id'], 'status': 'EXCLUDED', 'reason': EXCLUDE[e['id']], 'fill': tag}); continue
            s, cat, slot = e['site'], e['category'], e['id'].split('-')[-1]
            p = e['parameters']
            if cat == 'M':
                site_id = f"{TOWNCODE[s['town']]}-J{s['junction']}"
                out_road, out_lane = s['outgoing']
                mf, br = s['mainflow'], s['branch']
                notation = {'EGO': f"{mf['incoming']}/{lane(mf['from'])}→{mf['connecting']}/{lane(mf['to'])}→{out_road}/{lane(out_lane)}",
                            'NPC': f"{br['incoming']}/{lane(br['from'])}→{br['connecting']}/{lane(br['to'])}→{out_road}/{lane(out_lane)}"}
                actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), None, {'pose': 'PENDING_RUNTIME_QUERY'},
                                           {'connection': f"c{(mf if r == 'EGO' else br)['id']}",
                                            'notation': 'road/lane→connector/lane→outgoing/lane', 'route': notation[r]}, None)
                               for r in ('EGO', 'NPC'))
                why = f"fill {tag} ({commit}) series k={p['k']}; {e.get('k_rule', 'registered k')}"
                lref, g = spec_g(s['town'], br['connecting'], F(str(p['vN'])))
                e3 = (e3_ref,)
                params = {'G': ParameterProposal('G', (g,), 'm', why + '; spec 6.2 G0 with LrefN, ceil to 0.50 m (erratum 3, 06144be)', (prereg_ref, fill_ref, *e3), 'PROPOSED_PREREG_NOT_READY'),
                          'LrefN': ParameterProposal('LrefN', (lref,), 'm', 'spec 6.2: NPC connector road/@length (erratum 3)', (prereg_ref, *e3), 'PROPOSED_PREREG_NOT_READY'),
                          'vN': ParameterProposal('vN', (F(str(p['vN'])),), 'm/s', why, (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),
                          'vE': ParameterProposal('vE', (F(4),), 'm/s', 'mainflow E = 4 m/s (fill20 section 4)', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY')}
            else:  # F03
                own = f"{s['town']}-R{s['road']}-S{s['section']}"
                touching = [x['a'] if x['b'] == own else x['b'] for x in identity_pairs if x['touch'] and own in (x['a'], x['b'])]
                site_id = touching[0] if len(touching) == 1 else own
                assert len(touching) <= 1, touching
                route = {'road': s['road'], 'section': s['section'], 'lanes': s['lane'], 'travel': s['grade_run'],
                         'xpath': s['xpath'], 'direction': 'uphill (F2-4)'}
                actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), None, {'pose': 'PENDING_RUNTIME_QUERY'}, dict(route), None)
                               for r in ('EGO', 'NPC'))
                params = {'mechanism': ParameterProposal(e['mechanism'], (), '', e['parameters'], (prereg_ref,), 'APPROVED_PROPOSAL_NOT_READY')}
            bare = Candidate(e['id'], slot, '1', (f'FILL-{tag.upper()}-PREREG-{commit}',), cat, s['town'], site_id, actors, params, (),
                             {'poses': 'PENDING_RUNTIME_QUERY', 'destination': 'PENDING_RUNTIME_QUERY',
                              'weather_light': 'PENDING_RUNTIME_QUERY', 'selector': e['selector'], 'mechanism': e.get('mechanism')},
                             (fill_ref, prereg_ref))
            fields = [getattr(bare, f) for f in ('id', 'slot', 'version', 'lineage', 'category', 'town', 'site_id', 'actors',
                                                 'parameters', 'responses')]
            env = {**bare.environment, 'rationale_review': encode_record(attest(
                _digest(params), 'PARAMETER_RATIONALE', 'parameters are the registered series/spec inputs; no hand tuning'))}
            with_rationale = Candidate(*fields, env, bare.refs)
            env = {**env, 'selection_review': encode_record(attest(
                _digest(with_rationale), 'M56_SELECTION', f'generated by the pre-registered fill {tag} algorithm ({commit}); '
                'mechanical attestation, not an independent selector review'))}
            c = Candidate(*fields, env, bare.refs)
            try:
                if cat == 'M':
                    dest, responses, flags, _ = cr.junction_recipe(c, xodr[c.town])
                else:
                    dest, responses, flags, _ = cr.f_recipe(c, xodr[c.town])
            except Exception as ex:  # recorded, never guessed
                report.append({'id': c.id, 'status': 'RECIPE_ERROR', 'error': repr(ex)[:500]}); continue
            if any(f.startswith(('F03_DIRECTION_INVALID', 'OUTGOING_ROOM_BLOCKED')) for f in flags):
                report.append({'id': c.id, 'status': 'EXCLUDED', 'reason': 'RECIPE_FLAG', 'flags': list(flags)}); continue
            actors = tuple(replace(a, destination=dest.get(a.role), pose=None,
                                   pose_recipe={'pose': 'PENDING_RUNTIME_QUERY', 'at': 'route start (arc 0) + rest height + 1 cm'})
                           for a in c.actors)
            w = weather[c.town]
            env = {**{k: v for k, v in c.environment.items() if k not in ('weather', 'light', 'weather_light')},
                   'weather': w['weather'], 'light': w['light'], 'recipe_flags': tuple(flags)}
            c = replace(c, actors=actors, responses=responses, environment=env)
            if cat == 'M':
                ev = out / f'{c.id}-m-evidence.json'
                ev.write_text(json.dumps({'candidate': c.id, 'junction': s['junction'], 'town': s['town'], 'target_lane': s['outgoing'],
                                          'mainflow_dheading_deg': mf['dheading_deg'], 'branch_dheading_deg': br['dheading_deg'],
                                          'rule': f"fill {tag} ({commit}): R2 + F2-1 + F2-2 ({s['rule']})"}, indent=1), encoding='utf-8')
                mref = replace(cr.st.ref(ev, 'CATEGORY_EVIDENCE'), method='branch-to-mainflow-geometry-topology')
                rv = ReviewRecord(_digest((c.id, c.category, c.actors)), 'CATEGORY:M', (mref,), REVIEWER, '2026-10-24', 'APPROVED',
                                  (f"branch->mainflow: mainflow {mf['dheading_deg']:.1f} deg, branch {br['dheading_deg']:.1f} deg "
                                   f"({s['rule']})",), decision_ref)
                c = replace(c, environment={**c.environment, 'category_review': encode_record(rv)})
            adds.append(c)
            report.append({'id': c.id, 'status': 'ADDED', 'site': site_id, 'flags': list(flags), 'fill': tag})
    return adds, report


F25_REASON = ('re-bound 2026-11-07 after F2-5 (fill v2 prereg 409911e, approved 2026-10-24): the I/O index k is not a model '
              'unit, so it leaves the parameters; its value stays in every other parameter rationale (series, k=...)')


def f25_index_k(done):
    """F2-5 for the six fill20-v1 I/O candidates (I04/O04/I05/O05/I07/O07): they still carried k as a ParameterProposal
    with units 'index', which the product schema rejects (UNSUPPORTED_UNIT), so they never decoded. Same handling as the
    v2/v3 additions (k in the rationale, not a parameter). The parameter-rationale and selection reviews keep their
    evidence, reviewer and reasons and are re-bound to the new digests with F25_REASON (Claude under Duy's full
    delegation 2026-11-07; PREREG_M56_IO_RECIPE_V1_3_FILL_O addendum A). Other candidates: unchanged objects."""
    def rebind(raw, digest):
        raw = dict(raw) if isinstance(raw, Mapping) else json.loads(json.dumps(encode_record(raw), default=str))
        return {**raw, 'object_hash': digest, 'reasons': [*raw['reasons'], F25_REASON]}
    out = []
    for c in done:
        if any(p.units == 'index' for p in c.parameters.values()):
            c = replace(c, parameters={n: p for n, p in c.parameters.items() if p.units != 'index'})
            c = replace(c, environment={**c.environment, 'rationale_review': rebind(c.environment['rationale_review'], _digest(c.parameters))})
            bare = replace(c, environment={k: v for k, v in c.environment.items() if k != 'selection_review'})
            c = replace(c, environment={**c.environment, 'selection_review': rebind(c.environment['selection_review'], _digest(bare))})
        out.append(c)
    return out


# C0 erratum lanes (docs/m56/ERRATUM_M56_C0_C07_C08_LANES_20261108.md): in C07/C08 the catalog notation names OpenDRIVE
# Shoulder lanes (0.5 m wide), so no native route exists (NO_OUTGOING). Each Shoulder lane is replaced by the first
# Driving lane on the same side moving away from the reference line (same roads, connectors, junctions); the frozen v1
# EGO route is rebuilt from the corrected notation by the catalog's own junction_recipe. No other candidate changes.
C0_LANE_ERRATUM = {'M56-P-C07': {'EGO': '13/-3→453/-3→14/-3'},
                   'M56-P-C08': {'EGO': '55/+4→652/+4→54/+4', 'NPC': '50/-3→680/-3→51/-3'}}


ASEL2_FILL = __import__('os').environ.get('M56_ASEL2_FILL')  # A-SEL2 fill v4 output (PREREG_M56_FILL_V4_ASEL2_20261108)
ASEL2_PREREG = WORK / 'docs/m56/PREREG_M56_FILL_V4_ASEL2_20261108.md'


def asel2_io(e, cid, old, fill_ref, prereg_ref, attest, xodr, weather):
    """A-SEL2 I/O slot -> fill-format candidate (fill v3 conventions: route_recipe road/section/lanes/travel; parameters
    vE, vN, gap_m (I) or G_m + returnstart_m (O)); responses from catalog-recipes io_recipe on the site road section."""
    s, cat, slot = e['site'], e['category'], e['slot']
    k = e['k']; vE = F(6) * F(5, 4) ** (k - 1)
    why = f"fill v4 A-SEL2 slot {slot} k={k} (registered series, spec 7.4)"
    if cat == 'I':
        vals = {'vE': vE, 'vN': vE - 1, 'gap_m': F(6) * F(13, 10) ** (k - 1)}
    else:
        G = F(15) * F(13, 10) ** (k - 1)
        vals = {'vE': vE, 'vN': F(5, 2), 'G_m': G, 'returnstart_m': max(3 * vE, vE * (G + F(19, 2)) / (vE - F(5, 2)))}
    units = {'vE': 'm/s', 'vN': 'm/s', 'gap_m': 'm', 'G_m': 'm', 'returnstart_m': 'm'}
    params = {n: ParameterProposal(n, (v,), units[n], why, (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY') for n, v in vals.items()}
    route = {'road': s['road'], 'section': s['section'], 'lanes': list(s['lanes']), 'travel': s['travel'],
             'xpath': f"/OpenDRIVE/road[@id='{s['road']}']/lanes/laneSection[{s['section'] + 1}]",
             'chain_roads': list(s['roads']), 'junctions_crossed': list(s.get('junctions_crossed', ()))}
    actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), None, {'pose': 'PENDING_RUNTIME_QUERY'}, dict(route), None)
                   for r in ('EGO', 'NPC'))
    site_id = f"{s['town']}-R{s['road']}-S{s['section']}"
    bare = Candidate(cid, slot, '1', ('FILL-V4-ASEL2-PREREG-ddce811',) + ((old.id,) if old else ()), cat, s['town'], site_id,
                     actors, params, (), {'poses': 'PENDING_RUNTIME_QUERY', 'destination': 'PENDING_RUNTIME_QUERY',
                                         'weather_light': 'PENDING_RUNTIME_QUERY', 'selector': e['selector'],
                                         'asel2': {'predecessor': old.id if old else None, 'rule': e.get('rule'), 'k': k}},
                     (fill_ref, prereg_ref))
    fields = [getattr(bare, f) for f in ('id', 'slot', 'version', 'lineage', 'category', 'town', 'site_id', 'actors',
                                         'parameters', 'responses')]
    env = {**bare.environment, 'rationale_review': encode_record(attest(
        _digest(params), 'PARAMETER_RATIONALE', 'registered k series (spec 7.4); no hand tuning'))}
    with_rationale = Candidate(*fields, env, bare.refs)
    env = {**env, 'selection_review': encode_record(attest(
        _digest(with_rationale), 'M56_SELECTION', 'generated by the pre-registered fill v4 algorithm (03fb2ca + addendum A '
        'ddce811); mechanical attestation, not an independent selector review'))}
    c = Candidate(*fields, env, bare.refs)
    try:
        dest, responses, flags, _ = cr.io_recipe(c, xodr[c.town])
    except Exception as ex:  # recorded, never guessed
        return None, 'ERR:' + repr(ex)[:400]
    if any(f.startswith('WINDOW_TOO_SHORT') for f in flags):
        return None, 'RECIPE_FLAG:' + ','.join(flags)
    actors = tuple(replace(a, destination=dest.get(a.role), pose=None,
                           pose_recipe={'pose': 'PENDING_RUNTIME_QUERY', 'at': 'route start (arc 0) + rest height + 1 cm'})
                   for a in c.actors)
    w = weather[c.town]
    env = {**{k_: v for k_, v in c.environment.items() if k_ not in ('weather', 'light', 'weather_light')},
           'weather': w['weather'], 'light': w['light'], 'recipe_flags': tuple(flags)}
    return replace(c, actors=actors, responses=responses, environment=env), None


def asel2_additions(done, out, decision_ref, xodr, weather):
    """A-SEL2: C/L/M slots of the fill v4 output become candidates (junction_recipe, same path as the fill v2/v3 M
    additions). A slot that had a C0 candidate gets the successor id M56-P-<slot>-S1 and its predecessor leaves the run
    revision (recorded REPLACED_BY); an empty slot keeps M56-P-<slot>. I/O/F slots: not built here (report only)."""
    fill = json.loads(Path(ASEL2_FILL).read_text(encoding='utf-8'))
    fill_ref, prereg_ref = cr.st.ref(Path(ASEL2_FILL), 'M56_SELECTION_RECEIPT'), cr.st.ref(ASEL2_PREREG, 'PREREGISTRATION')
    def attest(digest, scope, why):
        return ReviewRecord(digest, scope, (fill_ref, prereg_ref), 'CLAUDE_MECHANICAL_ATTESTATION_UNDER_DUY_DELEGATION',
                            '2026-11-08', 'APPROVED', (why,), decision_ref)
    by_slot = {c.slot: c for c in done}
    keep, adds, report = list(done), [], []
    for e in fill['entries']:
        if e['status'] != 'PROPOSED' or e['category'] not in ('C', 'L', 'M', 'I', 'O'):
            report.append({'slot': e['slot'], 'status': 'ASEL2_NOT_BUILT', 'category': e['category'],
                           'reason': 'F builder pending' if e['status'] == 'PROPOSED' else e['status']}); continue
        s, cat, slot = e['site'], e['category'], e['slot']
        old = by_slot.get(slot)
        cid = f'M56-P-{slot}-S1' if old is not None else f'M56-P-{slot}'
        if cat in ('I', 'O') and __import__('os').environ.get('M56_ASEL2_IO') != '1':
            report.append({'slot': slot, 'status': 'ASEL2_NOT_BUILT', 'category': cat, 'reason': 'I/O build needs M56_ASEL2_IO=1'}); continue
        if cat in ('I', 'O'):
            c, why_not = asel2_io(e, cid, old, fill_ref, prereg_ref, attest, xodr, weather)
            if c is None:
                report.append({'id': cid, 'status': 'RECIPE_ERROR' if why_not.startswith('ERR') else 'EXCLUDED', 'reason': why_not}); continue
            if old is not None:
                keep = [x for x in keep if x.id != old.id]
                report.append({'id': old.id, 'status': 'REPLACED_BY', 'successor': cid})
            adds.append(c)
            report.append({'id': cid, 'status': 'ADDED', 'site': c.site_id, 'flags': list(c.environment.get('recipe_flags', ())), 'fill': 'v4'})
            continue
        site_id = f"{TOWNCODE[s['town']]}-J{s['junction']}"
        conn = {'EGO': s['ego'], 'NPC': s['npc']}
        actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), None, {'pose': 'PENDING_RUNTIME_QUERY'},
                                   {'connection': f"c{conn[r]['connecting']}", 'notation': 'road/lane→connector/lane→outgoing/lane',
                                    'route': s['notation'][r]}, None) for r in ('EGO', 'NPC'))
        d = {n: F(v) for n, v in e['descriptors'].items()}
        vE = F(2) if cat == 'L' else F(4)
        why = f"fill v4 A-SEL2 slot {slot} k={e['k']} (registered series); LrefN = NPC connector road/@length; G = derive_g"
        params = {'G': ParameterProposal('G', (d['G'],), 'm', why + '; spec 6.2 G0, ceil 0.50 m', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),
                  'LrefN': ParameterProposal('LrefN', (d['LrefN'],), 'm', 'spec 6.2: NPC connector road/@length', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),
                  'vN': ParameterProposal('vN', (d['vN'],), 'm/s', why, (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),
                  'vE': ParameterProposal('vE', (vE,), 'm/s', 'spec 6.1 Ego nominal (C/M 4, L 2)', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY')}
        bare = Candidate(cid, slot, '1', ('FILL-V4-ASEL2-PREREG-ddce811',) + ((old.id,) if old else ()), cat, s['town'], site_id,
                         actors, params, (), {'poses': 'PENDING_RUNTIME_QUERY', 'destination': 'PENDING_RUNTIME_QUERY',
                                             'weather_light': 'PENDING_RUNTIME_QUERY', 'selector': e['selector'],
                                             'asel2': {'predecessor': old.id if old else None, 'rule': e.get('rule')}},
                         (fill_ref, prereg_ref))
        fields = [getattr(bare, f) for f in ('id', 'slot', 'version', 'lineage', 'category', 'town', 'site_id', 'actors',
                                             'parameters', 'responses')]
        env = {**bare.environment, 'rationale_review': encode_record(attest(
            _digest(params), 'PARAMETER_RATIONALE', 'registered k series + spec 6.2 G0 from the pinned connector length; no hand tuning'))}
        with_rationale = Candidate(*fields, env, bare.refs)
        env = {**env, 'selection_review': encode_record(attest(
            _digest(with_rationale), 'M56_SELECTION', 'generated by the pre-registered fill v4 algorithm (03fb2ca + addendum A '
            'ddce811); mechanical attestation, not an independent selector review'))}
        c = Candidate(*fields, env, bare.refs)
        try:
            dest, responses, flags, _ = cr.junction_recipe(c, xodr[c.town])
        except Exception as ex:  # recorded, never guessed
            report.append({'id': cid, 'status': 'RECIPE_ERROR', 'error': repr(ex)[:500]}); continue
        if any(f.startswith('OUTGOING_ROOM_BLOCKED') for f in flags):
            report.append({'id': cid, 'status': 'EXCLUDED', 'reason': 'RECIPE_FLAG', 'flags': list(flags)}); continue
        actors = tuple(replace(a, destination=dest.get(a.role), pose=None,
                               pose_recipe={'pose': 'PENDING_RUNTIME_QUERY', 'at': 'route start (arc 0) + rest height + 1 cm'})
                       for a in c.actors)
        w = weather[c.town]
        env = {**{k: v for k, v in c.environment.items() if k not in ('weather', 'light', 'weather_light')},
               'weather': w['weather'], 'light': w['light'], 'recipe_flags': tuple(flags)}
        c = replace(c, actors=actors, responses=responses, environment=env)
        ev = out / f'{cid}-category-evidence.json'
        ev.write_text(json.dumps({'candidate': cid, 'category': cat, 'junction': s['junction'], 'town': s['town'],
                                  'ego_dheading_deg': s['ego'].get('dh', s['ego'].get('dheading_deg')),
                                  'npc_dheading_deg': s['npc'].get('dh', s['npc'].get('dheading_deg')),
                                  'rule': 'fill v4 3 (C: both straight, approaches 60-120 deg; L: EGO left, NPC opposite straight; '
                                          'M: fill v2 R2 + F2-1 + F2-2)'}, indent=1), encoding='utf-8')
        mref = cr.st.ref(ev, 'CATEGORY_EVIDENCE')
        if cat == 'M':
            mref = replace(mref, method='branch-to-mainflow-geometry-topology')
        rv = ReviewRecord(_digest((c.id, c.category, c.actors)), 'CATEGORY:' + cat, (mref,), REVIEWER, '2026-11-08', 'APPROVED',
                          (f'fill v4 category rule; connector headings recorded in {ev.name}',), decision_ref)
        c = replace(c, environment={**c.environment, 'category_review': encode_record(rv)})
        if old is not None:
            keep = [x for x in keep if x.id != old.id]
            report.append({'id': old.id, 'status': 'REPLACED_BY', 'successor': cid})
        adds.append(c)
        report.append({'id': cid, 'status': 'ADDED', 'site': site_id, 'flags': list(flags), 'fill': 'v4'})
    return keep + adds, report


def c0_erratum_lanes(done, xodr):
    out = []
    for c in done:
        fix = C0_LANE_ERRATUM.get(c.id)
        if fix:
            actors = tuple(replace(a, route_recipe={**a.route_recipe, 'route': fix[a.role],
                                                    'c0_erratum': f"{a.route_recipe['route']} (Shoulder lanes) -> {fix[a.role]}"})
                           if a.role in fix else a for a in c.actors)
            c = replace(c, actors=actors)
            dest, responses, flags, _ = cr.junction_recipe(c, xodr[c.town])
            c = replace(c, actors=tuple(replace(a, destination=dest.get(a.role)) for a in c.actors), responses=responses,
                        environment={**c.environment, 'recipe_flags': tuple(flags),
                                     'c0_erratum_lanes': 'ERRATUM_M56_C0_C07_C08_LANES_20261108 (Shoulder -> Driving)'})
        out.append(c)
    return out


def main(outdir, identity_path, *prep_dirs):
    out = Path(outdir); out.mkdir(parents=False, exist_ok=False)
    guard = {n: (rev2.V1.parent / n).read_bytes() for n in ('duy-decision-receipt.json', 'm01-r2-evidence.json')}
    try:
        done, b = rev2.v1_candidates(rev2.V1.parent)
    finally:
        changed = [n for n, data in guard.items() if (rev2.V1.parent / n).read_bytes() != data]
        for n in changed:
            (rev2.V1.parent / n).write_bytes(guard[n])
        assert not changed, f'V1_RECEIPT_BYTES_CHANGED_RESTORED:{changed}'
    v1 = json.loads(rev2.V1.read_text(encoding='utf-8'))['candidates']
    mine = json.loads(json.dumps([encode_record(c) for c in done], default=str))
    assert len(v1) == len(mine) and all(c == d for c, d in zip(v1, mine)), 'V1_REBUILD_MISMATCH'
    done = f25_index_k(done)
    import glob
    weather = {}
    for f in sorted(glob.glob(str(WORK / 'outputs/m56_native_weather_*/weather-light.json'))):
        weather.update(json.loads(Path(f).read_text(encoding='utf-8')))
    xodr = {t: v['opendrive_sha256'] for t, v in weather.items()}
    done = c0_erratum_lanes(done, xodr)
    identity = json.loads(Path(identity_path).read_text(encoding='utf-8'))
    decision = out / 'duy-v5-receipt.json'
    decision.write_text(json.dumps({
        'source': '[chat] 2026-10-24/25, user self-stated as Duy',
        'quotes': ['Release đầy đủ §11 (Recommended)', 'Consumer v5, PID tốc độ cao, Bổ sung cảnh tới 46',
                   'khỏi cần người khác bạn tự review', 'Duyệt 409911e (Recommended)',
                   'duyệt bản đăng ký trước fill v3 tại commit 4a26a66; chạy census đúng byte đó và ghi nguyên kết quả',
                   'bây giờ tôi đi ngủ có gì bạn tự quyết định các cảnh ... cứ làm theo các recommended về các cảnh của bạn'],
        'label': 'independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent'},
        indent=1, ensure_ascii=False), encoding='utf-8')
    dref = cr.st.ref(decision, 'OPERATOR_RECEIPT')
    adds, add_report = additions(out, dref, xodr, weather, identity['pairs'])
    done = done + adds
    if ASEL2_FILL:  # A-SEL2 fill v4 successors / new slots (C/L/M)
        done, a2_report = asel2_additions(done, out, dref, xodr, weather)
        add_report = list(add_report) + a2_report
    preps = rev2.prepared(prep_dirs)
    prereg_sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in RUNTIME_PREREGS}
    report = list(add_report)
    plain = rev2.plain
    for i, c in enumerate(done):
        if c.category not in ('C', 'L', 'M'):
            continue
        f, p = preps.get(c.id, (None, None))
        if p is None:
            status = {'status': 'BLOCKED_FIXTURE', 'reason': 'NOT_PREPARED', 'prereg_sha256': prereg_sha}
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': status})
            report.append({'id': c.id, 'status': 'BLOCKED_FIXTURE', 'reason': 'NOT_PREPARED'}); continue
        pref = {'prepare_json': str(f), 'prepare_sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'prereg_sha256': prereg_sha}
        if p['status'] != 'PREPARED':
            status = {'status': p['status'], 'reason': p.get('reason'), **pref}
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': status})
            report.append({'id': c.id, 'status': p['status'], 'reason': p.get('reason'), 'prepare_sha256': pref['prepare_sha256']}); continue
        markers = {k: plain(v) for k, v in p['markers'].items()}
        readiness = {'targets_mps': {k: plain(v) for k, v in p['targets'].items()}, 'markers_m': markers}
        actors = tuple(replace(a, destination=F(p['destinations'][a.role]),
                               route_recipe={**a.route_recipe, **({'v2_start': 'probe-1 route cut at station '
                                                                    f"{plain(p['npc_start_station_probe1'])!r} (phasing rule, prereg 3)"}
                                                                   if a.role == 'NPC' else {'v2_start': 'frozen v1 arc 0'}),
                                             'v2_routes_sha256': p['routes_v2_sha256']})
                       for a in c.actors)
        status = {'status': 'PREPARED', **pref}
        phase = {'phase_predicate': p['phase_predicate']} if p.get('phase_predicate') else {}
        if p.get('phase_predicate') and p.get('phase_wait_limit_s') and float(plain(p['phase_wait_limit_s'])) > 60:
            phase['phase_wait_limit_s'] = F(str(round(float(plain(p['phase_wait_limit_s'])), 3)))
        responses = c.responses
        if p.get('recipe') == 'v3':
            from native_v2_common import v2_routes
            routes, _, _ = v2_routes(p, {a.role: a.route_recipe['route'] for a in c.actors}, c.town, plain)
            responses = tuple(cr.hashed(replace(r, route=routes['EGO'])) if r.actor_role == 'EGO' else r for r in c.responses)
            status['recipe'] = 'v3'
        if p.get('npc_longitudinal'):
            status['npc_longitudinal'] = p['npc_longitudinal']  # v5 P-NPC, recorded per scene
        done[i] = replace(c, actors=actors, responses=responses,
                          environment={**c.environment, 'readiness': readiness, 'runtime_recipe_v2': status, **phase})
        report.append({'id': c.id, 'status': 'PREPARED', 'markers': {k: str(v) for k, v in markers.items()},
                       'npc_longitudinal': p.get('npc_longitudinal')})
    # The CATEGORY:M review binds (id, category, actors); applying a preparation replaces the actors (destination, route
    # recipe), so the same review (same evidence, reviewer, reasons) is re-bound to the final actors.
    for i, c in enumerate(done):
        raw = c.environment.get('category_review')
        if c.category == 'M' and isinstance(raw, Mapping):
            want = _digest((c.id, c.category, c.actors))
            if raw.get('object_hash') != want:
                rv = {**raw, 'object_hash': want, 'reasons': [*raw['reasons'], 're-bound to the actors after the runtime recipe']}
                done[i] = replace(c, environment={**c.environment, 'category_review': rv})
    # I/O tooling (docs/m56/DESIGN_M56_IO_TOOLING_20261026.md): an I/O candidate with an 'io-v1' preparation gets its
    # native responses (frozen program/targets/profiles on the native routes, one catalog-arc offset), readiness and
    # destinations; one without stays byte-identical. Preparation only: no I/O A/B before Duy approves the I/O recipe.
    from native_io_common import io_routes, catalog_offset, io_responses, io_geometry
    for i, c in enumerate(done):
        f, p = preps.get(c.id, (None, None))
        if c.category not in ('I', 'O') or p is None or p.get('recipe') != 'io-v1':
            continue
        pref = {'prepare_json': str(f), 'prepare_sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'recipe': 'io-v1'}
        if p['status'] != 'PREPARED':
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': {'status': p['status'], 'reason': p.get('reason'), **pref}})
            report.append({'id': c.id, 'status': p['status'], 'reason': p.get('reason')}); continue
        pp = {k: (v if k == 'poses' else plain(v)) for k, v in p.items()}
        routes, _, _ = io_routes(pp, plain, c.town)
        d = catalog_offset(c, routes, pp)
        geo = io_geometry(c, pp, routes, d, plain)
        if geo.get('reason'):
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': {'status': 'BLOCKED_FIXTURE', 'reason': geo['reason'], **pref}})
            report.append({'id': c.id, 'status': 'BLOCKED_FIXTURE', 'reason': geo['reason']}); continue
        readiness = {'targets_mps': {k: plain(v) for k, v in p['targets'].items()},
                     'markers_m': {k: plain(v) for k, v in p['markers'].items()}}
        actors = tuple(replace(a, destination=routes[a.role].destination,
                               route_recipe={**a.route_recipe, 'io_recipe': 'io-v1', 'catalog_offset_m': str(d),
                                             'v2_routes_sha256': p['routes_v2_sha256']}) for a in c.actors)
        done[i] = replace(c, actors=actors, responses=io_responses(c, routes, d),
                          environment={**c.environment, 'readiness': readiness,
                                       'runtime_recipe_v2': {'status': 'PREPARED', 'catalog_offset_m': str(d), **pref}})
        report.append({'id': c.id, 'status': 'PREPARED', 'recipe': 'io-v1', 'catalog_offset_m': str(d)})
    revision = CandidateRevision('c0-partial-v5: retained-23+fill20-v1-minus-F02-F03+fill-v2/v3+recipes+runtime-recipe-v5',
                                 tuple(done), 'x' * 64, None)
    ev = (cr.st.ref(rev2.EV1, 'IDENTITY_EVIDENCE'), cr.st.ref(rev2.EV2, 'IDENTITY_EVIDENCE'), cr.st.ref(identity_path, 'IDENTITY_EVIDENCE'))
    rules = {'id': 'touching-cross-section-v1', 'rule': 'same physical place iff modelled XODR cross-sections touch/overlap',
             'evidence_sha256': [r.sha256 for r in ev]}
    method = IdentityMethod('touching-cross-section-v1', '1', _digest(rules), rules)
    sites, assignments = {}, {}
    for c in done:
        if c.site_id not in sites:
            rec = SiteRecord(c.site_id, 'JUNCTION' if c.site_id.startswith('P') and '-J' in c.site_id else 'NONJUNCTION',
                             {'town': c.town, 'site': c.site_id}, {'method_hash': method.hash}, ev, None)
            rv = ReviewRecord(_site_digest(rec), 'SITE_IDENTITY', ev, REVIEWER, '2026-10-24', 'APPROVED',
                              ('distinct physical place under touching-cross-section-v1',), dref)
            sites[c.site_id] = replace(rec, review=rv)
        assignments[c.id] = c.site_id
    packet_path = out / 'site-ledger-packet.json'
    packet_path.write_text(json.dumps({'method_hash': method.hash, 'records': [encode_record(x) for x in sites.values()],
                                       'assignments': assignments}, indent=1, sort_keys=True, default=str), encoding='utf-8')
    pref = cr.st.ref(packet_path, 'IDENTITY_LEDGER_PACKET')
    ledger = review_sites(revision, method, (ReviewRecord(pref.sha256, 'IDENTITY_LEDGER', (pref,), REVIEWER, '2026-10-24',
                                                          'APPROVED', ('ledger for the v5 revision',), dref),))
    addendum = cr.st.ref(WORK / 'docs/m56/SPEC_ADDENDUM_C0_PARTIAL_20261022.md', 'SPEC_ADDENDUM')
    review = ReviewRecord(_digest({'revision': revision, 'sites': ledger}), 'C0', (addendum, pref, dref), REVIEWER, '2026-10-25',
                          'APPROVED', ('C0 partial v5 = v4 + fill v2/v3 additions with complete recipes + runtime-recipe v5; '
                                       'review by Claude under Duy delegation, independent review waived by Duy 2026-10-24',), dref)
    from m56.catalog import _category_proven
    unproven = [c.id for c in done if c.category == 'M' and not _category_proven(c, 'M')]
    if unproven:
        print('M_UNPROVEN', unproven)
    frozen = freeze_c0(revision, ledger, review, partial=addendum)
    if __import__('os').environ.get('M56_AUDIT') == '1':
        # 2026-11-08 product offline audit (audit_diversity + check_catalog), never a release. No inter-scene descriptor
        # specs were ever authored or approved, so the PolicyBundle carries none (every comparison is reported as the
        # product computes it, BLOCKED_COMPARABILITY expected), and no DECLARED_COMPARABILITY_D09 review exists.
        from collections import Counter
        from m56.catalog import audit_diversity, check_catalog, summarize
        from m56.model import PolicyBundle
        pol = PolicyBundle('m56-audit-no-descriptor-specs', 'f' * 64, {}, {}, {}, (addendum,))
        comps = audit_diversity(revision, pol, ())
        aud = check_catalog(revision, ledger, comps)
        summ = summarize(frozen if not hasattr(frozen, 'reasons') else revision, aud, ())
        (out / 'audit-report.json').write_text(json.dumps({
            'note': 'offline product audit; never a release', 'status': aud.status, 'counts': dict(aud.counts),
            'towns': dict(aud.towns), 'deficits': list(aud.deficits), 'comparisons': len(comps),
            'comparison_status': dict(Counter(c.status for c in comps)),
            'comparisons_by_category': dict(Counter(next(x.category for x in done if x.id == c.pair_ids[0]) for c in comps)),
            'release_summary': summ}, indent=1, default=str, ensure_ascii=False), encoding='utf-8')
        print('AUDIT', aud.status, dict(aud.counts), list(aud.deficits), dict(Counter(c.status for c in comps)), summ['deficits'])
    summary = {'candidates': len(done), 'sites': len(sites), 'junction_sites': sum(x.kind == 'JUNCTION' for x in sites.values())}
    (out / 'v5-report.json').write_text(json.dumps({'summary': summary, 'rows': report}, indent=1, default=str, ensure_ascii=False),
                                        encoding='utf-8')
    if hasattr(frozen, 'reasons'):
        print('FREEZE_BLOCKED', list(frozen.reasons), summary); return
    data = json.dumps(encode_record(frozen), indent=1, sort_keys=True, default=str).encode()
    with open(out / 'c0-partial-v5-frozen-revision.json', 'xb') as f:
        f.write(data)
    print('C0_PARTIAL_V5_FROZEN', frozen.c0_receipt.kind, summary, hashlib.sha256(data).hexdigest())
    print(json.dumps([r for r in report if r['status'] != 'PREPARED'], default=str, ensure_ascii=False)[:3000])


if __name__ == '__main__':
    main(*sys.argv[1:])
