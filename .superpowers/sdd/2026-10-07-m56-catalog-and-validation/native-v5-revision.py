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
TOWNCODE = {'Town04': 'P04', 'Town05': 'P05', 'Town06': 'P06', 'Town07': 'P07'}
RUNTIME_PREREGS = [WORK / 'docs/m56' / n for n in ('PREREG_M56_RUNTIME_RECIPE_V2_20261023.md', 'PREREG_M56_V5_CONSUMER_PID_20261024.md',
                                                    'PREREG_M56_V5_ERRATUM1_C3_20261024.md', 'PREREG_M56_V5_ERRATUM2_EGO_PID_20261024.md')]


def lane(x):
    return f'{x:+d}'


def additions(out, decision_ref, xodr, weather, identity_pairs):
    adds, report = [], []
    for tag, (fill_path, prereg_path, commit) in FILLS.items():
        fill_ref, prereg_ref = cr.st.ref(fill_path, 'M56_SELECTION_RECEIPT'), cr.st.ref(prereg_path, 'PREREGISTRATION')

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
                params = {'G': ParameterProposal('G', (F(str(p['GL_m'])),), 'm', why + '; G = GL (fill20 section 3/4)', (prereg_ref, fill_ref), 'PROPOSED_PREREG_NOT_READY'),
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
    import glob
    weather = {}
    for f in sorted(glob.glob(str(WORK / 'outputs/m56_native_weather_*/weather-light.json'))):
        weather.update(json.loads(Path(f).read_text(encoding='utf-8')))
    xodr = {t: v['opendrive_sha256'] for t, v in weather.items()}
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
    revision = CandidateRevision('c0-partial-v5: retained-23+fill20-v1-minus-F02-F03+fill-v2/v3+recipes+runtime-recipe-v5',
                                 tuple(done), 'x' * 64, None)
    ev = (cr.st.ref(rev2.EV1, 'IDENTITY_EVIDENCE'), cr.st.ref(rev2.EV2, 'IDENTITY_EVIDENCE'), cr.st.ref(identity_path, 'IDENTITY_EVIDENCE'))
    rules = {'id': 'touching-cross-section-v1', 'rule': 'same physical place iff modelled XODR cross-sections touch/overlap',
             'evidence_sha256': [r.sha256 for r in ev]}
    method = IdentityMethod('touching-cross-section-v1', '1', _digest(rules), rules)
    sites, assignments = {}, {}
    for c in done:
        if c.site_id not in sites:
            rec = SiteRecord(c.site_id, 'JUNCTION' if c.site_id.startswith('P0') else 'NONJUNCTION',
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
    frozen = freeze_c0(revision, ledger, review, partial=addendum)
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
