"""Catalog admission on artificial inputs, not scene selection or G3 evidence."""


def test_corridors_do_not_close_junction_gate(require,catalog_case):
    check=require('m56.catalog','check_catalog')
    c=catalog_case(junctions=20)
    out=check(c.revision,c.sites,c.comparisons)
    assert out.counts['qualified_junctions']==20
    assert 'JUNCTION_SHORTFALL' in out.deficits
    assert out.status!='RELEASE_ELIGIBLE'


def test_26_candidates_not_c0(require,catalog_case):
    freeze=require('m56.catalog','freeze_c0')
    c=catalog_case(count=26)
    out=freeze(c.revision,c.sites,c.review)
    assert out.status=='C0_BLOCKED'
    assert c.revision.c0_receipt is None


def test_opt_not_extra_town(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case(count=4)
    revision=replace(c.revision,candidates=tuple(replace(candidate,town=town)
        for candidate,town in zip(c.revision.candidates,('Town04','Town04_Opt','Town05','Town05_Opt'))))
    assert check(revision,c.sites,()).counts['distinct_towns']==2


def test_town03_rejected(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    revision=replace(c.revision,candidates=(replace(c.revision.candidates[0],town='Town03'),)+c.revision.candidates[1:])
    assert 'TOWN_NOT_ALLOWED' in check(revision,c.sites,()).deficits


def test_category_town_fourth_rejected(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    revision=replace(c.revision,candidates=tuple(replace(x,town='Town04') if i<4 else x
                        for i,x in enumerate(c.revision.candidates)))
    assert 'CATEGORY_TOWN_CAP' in check(revision,c.sites,()).deficits


def test_same_site_io_third_rejected(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    ids=('I01','O01','F01')
    assignments=dict(c.sites.assignments)
    assignments.update({key:'SYNTHETIC_SITE_00' for key in ids})
    revision=replace(c.revision,candidates=tuple(replace(x,site_id='SYNTHETIC_SITE_00')
                     if x.id in ids else x for x in c.revision.candidates))
    assert 'SITE_CAP' in check(revision,replace(c.sites,assignments=assignments),()).deficits


def test_xml_alias_cannot_bypass_cap(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    # Separate IDs with the same reviewed physical interaction domain, not merely nearby XY.
    records=list(c.sites.records)
    for i in (1,2):
        records[i]=replace(records[i],geography=records[0].geography,
                           topology=records[0].topology)
    out=check(c.revision,replace(c.sites,records=tuple(records)),())
    assert 'SITE_CAP' in out.deficits
    assert out.counts['qualified_junctions']<23


def test_true_merge_not_common_output_lane(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    revision=replace(c.revision,candidates=tuple(replace(x,environment={
        'kind':'SYNTHETIC_TEST','common_output_lane':'same'}) if x.category=='M' else x
        for x in c.revision.candidates))
    assert 'M_CATEGORY_UNPROVEN' in check(revision,c.sites,()).deficits


def test_site_method_frozen_before_validation(require,catalog_case):
    from dataclasses import replace
    freeze=require('m56.catalog','freeze_c0')
    c=catalog_case()
    out=freeze(c.revision,replace(c.sites,freeze_ref=None),c.review)
    assert out.status=='C0_BLOCKED'
    assert 'IDENTITY_METHOD_NOT_FROZEN' in out.reasons


def test_load_candidates_rejects_unknown_fields(require,tmp_path):
    load=require('m56.catalog','load_candidates')
    path=tmp_path/'catalog.json'
    path.write_text('{"approved":true}')
    out=load(path)
    assert out.status=='SCHEMA_ERROR'
    assert out.errors[0].reason=='UNKNOWN_FIELD'


def test_c0_incomplete_recipe_blocked_even_with_bound_review(require,catalog_case):
    from dataclasses import replace
    import hashlib,json
    from m56.model import encode_record
    freeze=require('m56.catalog','freeze_c0')
    c=catalog_case()
    revision=replace(c.revision,candidates=tuple(replace(x,actors=(),responses=()) for x in c.revision.candidates))
    digest=hashlib.sha256(json.dumps(encode_record(revision),sort_keys=True,
                         separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    out=freeze(revision,c.sites,c.review_factory(digest,'C0'))
    assert out.status=='C0_BLOCKED'
    assert 'INCOMPLETE_CANDIDATE_RECIPE' in out.reasons


def test_review_sites_needs_bound_file_receipts(require,catalog_case,tmp_path):
    import hashlib,json
    from dataclasses import replace
    from m56.model import encode_record,SourceRef
    review_sites=require('m56.catalog','review_sites')
    c=catalog_case()
    payload={'method_hash':c.sites.method.hash,'records':encode_record(c.sites.records),
             'assignments':dict(c.sites.assignments)}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    path=tmp_path/'sites.json';path.write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    ref=SourceRef(str(path),digest,len(raw),'test','identity-packet','SYNTHETIC_TEST')
    review=replace(c.review_factory(digest,'IDENTITY_LEDGER'),refs=(ref,))
    out=review_sites(c.revision,c.sites.method,(review,))
    assert len(out.records)==23
    assert out.assignments['C01']=='SYNTHETIC_SITE_00'
    assert out.freeze_ref==ref
    path.write_bytes(b'changed')
    failed=review_sites(c.revision,c.sites.method,(review,))
    assert failed.freeze_ref is None
    assert not failed.records


def test_c0_complete_recipes_do_not_require_qualified_junctions(require,catalog_case):
    from dataclasses import replace
    from fractions import Fraction
    import hashlib,json
    from m56.model import encode_record,ParameterProposal
    freeze=require('m56.catalog','freeze_c0')
    check=require('m56.catalog','check_catalog')
    c=catalog_case(junctions=20)
    def digest(value):
        return hashlib.sha256(json.dumps(encode_record(value),sort_keys=True,
                     separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    candidates=[]
    for candidate in c.revision.candidates:
        review=c.review_factory(digest((candidate.id,candidate.category,candidate.actors)),
                                'CATEGORY:'+candidate.category)
        review=replace(review,refs=(replace(c.ref,method='branch-to-mainflow-geometry-topology'),))
        candidates.append(replace(candidate,parameters={'v':ParameterProposal('v',(Fraction(4),),
                         'm/s','synthetic only',(c.ref,),'APPROVED_PROPOSAL_NOT_READY')},
                         responses=tuple(replace(r,targets={'nominal':Fraction(4)},
                                        phases={'trigger':'SYNTHETIC_TEST'}) for r in candidate.responses),
                         environment={'weather':{'kind':'SYNTHETIC_TEST'},
                                      'light':{'kind':'SYNTHETIC_TEST'},'category_review':encode_record(review)}))
    sites=replace(c.sites,records=tuple(replace(s,review=replace(s.review,scope='SITE_IDENTITY'))
                                      for s in c.sites.records))
    revision=replace(c.revision,candidates=tuple(candidates))
    review=c.review_factory(digest({'revision':revision,'sites':sites}),'C0')
    out=freeze(revision,sites,review)
    assert hasattr(out,'c0_receipt'),out
    assert out.c0_receipt is not None
    assert revision.c0_receipt is None
    audit=check(out,sites,())
    assert audit.counts['eligible']==0
    assert audit.counts['qualified_junctions']==0
    assert 'JUNCTION_SHORTFALL' in audit.deficits
    changed=replace(sites,assignments={**sites.assignments,'C01':'SYNTHETIC_SITE_02'})
    assert freeze(revision,changed,review).status=='C0_BLOCKED'


def test_adjacent_speed_does_not_supply_second_parameter(require,parameter_case):
    from fractions import Fraction
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    out=compare(c.a,c.b,c.policies,())
    assert out.deltas==(Fraction(1,5),Fraction(7,52))
    assert out.status=='DIVERSITY_DEFICIT'


def test_near_zero_needs_review(require,parameter_case):
    from dataclasses import replace
    from fractions import Fraction as F
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    a=replace(c.a,parameters={k:replace(v,values=(F('1e-12'),)) for k,v in c.a.parameters.items()})
    b=replace(c.b,parameters={k:replace(v,values=(F('2e-12'),)) for k,v in c.b.parameters.items()})
    assert compare(a,b,c.policies,()).status=='REVIEW_REQUIRED'


def test_zero_zero_not_credit(require):
    delta=require('m56.catalog','delta')
    assert delta(0,0) is None
    assert delta(-1,2) is None
    assert delta(float('nan'),2) is None
    assert delta(True,2) is None


def test_display_rounding_cannot_rescue(require):
    from fractions import Fraction as F
    delta=require('m56.catalog','delta')
    assert delta(F(1),F('0.8000000001'))<F(1,5)
    assert delta(F(1),F('0.8'))==F(1,5)


def test_current_G_deficits_preserved(require):
    from fractions import Fraction as F
    from itertools import combinations
    delta=require('m56.catalog','delta')
    gs={'C':['26','22.5','18.5','20','16.5','16','15.5','15.5'],
        'L':['11','9.5','11','9','7','5.5','5','4.5'], 'M':['46','40','24.5','17.5']}
    sufficient={cat:sum(delta(a,b)>=F(1,5) for a,b in combinations(map(F,values),2))
                for cat,values in gs.items()}
    assert sufficient=={'C':13,'L':19,'M':5}
    assert {cat:len(list(combinations(values,2))) for cat,values in gs.items()}=={'C':28,'L':28,'M':6}


def test_io_sections_include_both_lengths(require):
    from fractions import Fraction as F
    derive=require('m56.catalog','derive_io_section')
    assert derive('O',F('9.375'),F('2.5'),F('25.35'),F(170),-3)==F(21947,88)


def test_missing_descriptor_blocks(require,parameter_case):
    from dataclasses import replace
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    incomplete={k:{f:v for f,v in desc.items() if f!='aggregation'}
                 for k,desc in c.policies.descriptor_specs.items()}
    assert compare(c.a,c.b,replace(c.policies,descriptor_specs=incomplete),()).status=='BLOCKED_COMPARABILITY'


def test_155_unique_pairs(require,catalog_case,parameter_case):
    audit=require('m56.catalog','audit_diversity')
    c=catalog_case();p=parameter_case()
    comparisons=audit(c.revision,p.policies,())
    keys=[tuple(sorted(item.pair_ids)) for item in comparisons]
    assert len(keys)==len(set(keys))==155


def test_g_uses_ceiling_half_metre_and_approved_terms(require):
    from fractions import Fraction as F
    derive=require('m56.catalog','derive_g')
    assert derive(F(4),F(3),F('21.96'))==26
    assert derive(F(2),F(3),F('18.77'))==11
    assert derive(F(4),F(3),F('51.69'))==46


def test_all_approved_g_and_io_proposals_derive_exactly(require):
    from fractions import Fraction as F
    g=require('m56.catalog','derive_g')
    io=require('m56.catalog','derive_io_section')
    rows=[(4,['21.96','22.01','19.37','29.81','25.92','31.78','36.81','47.88'],
               ['26','22.5','18.5','20','16.5','16','15.5','15.5']),
          (2,['18.77','18.21','32.27','30.13','25.11','16.8','19.36','18.002049'],
               ['11','9.5','11','9','7','5.5','5','4.5']),
          (4,['51.69','54.438478','33.75','23.094619'],['46','40','24.5','17.5'])]
    for ego,lengths,expected in rows:
        for k,(length,want) in enumerate(zip(lengths,expected)):
            assert g(F(ego),3*F(5,4)**k,F(length))==F(want)
    for category,e,n,gap,s,lane,want in [
        ('I','6','5','6','320',4,F(1097,4)),
        ('I','7.5','6.5','7.8','380',3,F(1295,4)),
        ('I','9.375','8.375','10.14','160',-4,F(1835,8)),
        ('O','6','2.5','15','280',3,F(865,4)),
        ('O','7.5','2.5','19.5','360',2,F(1161,4)),
        ('O','9.375','2.5','25.35','170',-3,F(21947,88))]:
        assert io(category,F(e),F(n),F(gap),F(s),lane)==want


def test_unapproved_parameter_not_counted(require,parameter_case):
    from dataclasses import replace
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    a=replace(c.a,parameters={k:replace(v,status='UNAPPROVED') for k,v in c.a.parameters.items()})
    assert compare(a,c.b,c.policies,()).status=='BLOCKED_COMPARABILITY'


def test_duplicate_physical_quantity_not_two_parameters(require,parameter_case):
    from dataclasses import replace
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    descriptors={name:{**desc,'physical_quantity':'same_gap'} for name,desc in c.policies.descriptor_specs.items()}
    assert compare(c.a,c.b,replace(c.policies,descriptor_specs=descriptors),()).status=='BLOCKED_COMPARABILITY'


def test_review_is_bound_to_values_and_policy(require,parameter_case):
    from dataclasses import replace
    from fractions import Fraction as F
    import hashlib,json
    from m56.model import encode_record,ReviewRecord
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    b=replace(c.b,parameters={k:replace(v,values=(v.values[0]*2,)) for k,v in c.b.parameters.items()})
    binding=hashlib.sha256(json.dumps(encode_record({'a':c.a,'b':b,'policy':c.policies}),
                  sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    review=ReviewRecord(binding,'DECLARED_COMPARABILITY_D09',(c.ref,),'SYNTHETIC_TEST','2026-10-08',
                 'APPROVED',('units/physical meaning/near-zero reviewed on synthetic input',),c.ref)
    assert compare(c.a,b,c.policies,(review,)).status=='PASS'
    modified=replace(b,version='modified')
    assert compare(c.a,modified,c.policies,(review,)).status=='REVIEW_REQUIRED'


def test_tenth_successor_admitted_under_asel2(require,replacement_case):
    # m56-v10 = spec addendum A-SEL2 (Duy 2026-11-08): shared successor budget 150 (spec original: exactly 9).
    admit=require('m56.catalog','admit_successor')
    c=replacement_case(9)
    out=admit(c.ledger,c.transaction,c.review)
    assert out.status=='ADMITTED'
    assert out.ledger.used==10


def test_151st_successor_never_admitted(require,replacement_case):
    admit=require('m56.catalog','admit_successor')
    c=replacement_case(150)
    out=admit(c.ledger,c.transaction,c.review)
    assert out.status=='REPLACEMENT_LIMIT'
    assert out.ledger.used==150
    assert len(out.ledger.transactions)==150


def test_pre_post_share_one_counter(require,replacement_case):
    admit=require('m56.catalog','admit_successor')
    c=replacement_case(8)
    out=admit(c.ledger,c.transaction,c.review)
    assert out.status=='ADMITTED'
    assert out.ledger.used==9
    assert c.ledger.used==8


def test_failed_successor_still_consumes(require,replacement_case):
    admit=require('m56.catalog','admit_successor')
    c=replacement_case(3)
    out=admit(c.ledger,c.transaction,c.review)
    # Charge is immediate, before any fixture/action success is available.
    # A second admission to the same slot after failure must consume again.
    assert out.ledger.used==4
    next_tx=c.proposal(out.ledger)
    second=admit(out.ledger,next_tx,c.review_for(out.ledger,next_tx))
    assert second.ledger.used==5
    assert len({x.slot for x in second.ledger.transactions})==1


def test_restart_cannot_reset_ledger(require,replacement_case):
    admit=require('m56.catalog','admit_successor')
    from m56.model import encode_record,decode_record
    c=replacement_case(150)
    restored=decode_record('ReplacementLedger',encode_record(c.ledger))
    out=admit(restored,c.transaction,c.review)
    assert out.ledger.used==150
    assert out.status=='REPLACEMENT_LIMIT'


def test_harness_fix_not_scene_replacement(require,replacement_case):
    from m56.model import EpisodeVerdict
    classify=require('m56.catalog','classify_failure')
    c=replacement_case(3)
    verdict=EpisodeVerdict('UNKNOWN','UNKNOWN','INVALID',('HARNESS_CORRELATION_ERROR',),(),{})
    import hashlib,json
    from m56.model import encode_record,ReviewRecord
    digest=hashlib.sha256(json.dumps(encode_record(verdict),sort_keys=True,
                    separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    review=ReviewRecord(digest,'UNCHANGED_SCENE_HARNESS_FIX',(c.ref,),'SYNTHETIC_TEST',
          '2026-10-08','APPROVED',('scene and protocol unchanged; new technical version only',),c.ref)
    assert classify(verdict,review)=='TECHNICAL_FIX_NO_RERUN'
    assert c.ledger.used==3


def test_pre_c0_action_trial_rejected(require,catalog_case):
    guard=require('m56.catalog','validation_precondition')
    c=catalog_case(count=26)
    assert guard(c.revision).status=='BLOCKED_C0'


def test_tampered_history_cannot_be_admitted(require,replacement_case):
    from dataclasses import replace
    admit=require('m56.catalog','admit_successor')
    c=replacement_case(3)
    history=(replace(c.ledger.transactions[0],counters=(5,6)),)+c.ledger.transactions[1:]
    changed=replace(c.ledger,transactions=history)
    out=admit(changed,c.transaction,c.review_for(changed,c.transaction))
    assert out.status=='INVALID_LEDGER'
    assert out.ledger==changed


def test_asel2_towns_allowed_town03_still_not(require,catalog_case):
    from dataclasses import replace
    check=require('m56.catalog','check_catalog')
    c=catalog_case()
    big=replace(c.revision,candidates=(replace(c.revision.candidates[0],town='Town12'),)+c.revision.candidates[1:])
    assert 'TOWN_NOT_ALLOWED' not in check(big,c.sites,()).deficits
    bad=replace(c.revision,candidates=(replace(c.revision.candidates[0],town='Town03'),)+c.revision.candidates[1:])
    assert 'TOWN_NOT_ALLOWED' in check(bad,c.sites,()).deficits


def test_asel2_descriptor_sets_by_category_and_aliases(require,parameter_case):
    # A-SEL2 4: one descriptor set per category; a descriptor may name parameter aliases (gap / gap_m).
    from dataclasses import replace
    compare=require('m56.catalog','compare_parameters')
    c=parameter_case()
    flat=compare(c.a,c.b,c.policies,())
    by_cat=replace(c.policies,descriptor_specs={'by_category':{c.a.category:dict(c.policies.descriptor_specs)}})
    assert compare(c.a,c.b,by_cat,()).status==flat.status
    other=replace(c.policies,descriptor_specs={'by_category':{'Z':dict(c.policies.descriptor_specs)}})
    assert compare(c.a,c.b,other,()).status=='BLOCKED_COMPARABILITY'
    name=next(iter(c.policies.descriptor_specs))
    renamed=lambda x:replace(x,parameters={(name+'_m' if k==name else k):v for k,v in x.parameters.items()})
    aliased={k:({**d,'aliases':(k+'_m',)} if k==name else d) for k,d in c.policies.descriptor_specs.items()}
    assert compare(renamed(c.a),renamed(c.b),replace(c.policies,descriptor_specs=aliased),()).values==flat.values
    assert compare(renamed(c.a),renamed(c.b),c.policies,()).status=='BLOCKED_COMPARABILITY'


def _realized_setup(parameter_case, tmp_path, va, vb):
    import hashlib
    from dataclasses import replace
    from fractions import Fraction as F
    from m56.model import SourceRef
    c = parameter_case()
    raw = tmp_path / 'raw.json'; raw.write_bytes(b'{"frames": 1}')
    ref = SourceRef(str(raw), hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_size, '1', 'sha256', 'NATIVE_RAW')
    d = lambda q: {'unit': 'm', 'source_actions': ('A', 'B'), 'aggregation': 'mean_of_A_and_B', 'event': 't0',
                   'window': 'at t0', 'reference': 'test', 'physical_quantity': q, 'refs': (ref,)}
    pol = replace(c.policies, descriptor_specs={'realized_by_category': {c.a.category: {'x': d('qx'), 'y': d('qy')}}})
    realized = {c.a.id: {'x': {'A': (F(va[0]), ref), 'B': (F(va[1]), ref)}, 'y': {'A': (F(10), ref), 'B': (F(10), ref)}},
                c.b.id: {'x': {'A': (F(vb[0]), ref), 'B': (F(vb[1]), ref)}, 'y': {'A': (F(20), ref), 'B': (F(20), ref)}}}
    return c, pol, realized, ref


def test_asel2_realized_mean_of_both_actions(require, parameter_case, tmp_path):
    from fractions import Fraction as F
    compare = require('m56.catalog', 'compare_realized')
    # a: A=10, B=14 -> mean 12; b: A=15, B=15 -> 15; Delta = 3/15 = 0.2 exactly (no epsilon); y: 10 vs 20 -> 0.5
    c, pol, realized, _ = _realized_setup(parameter_case, tmp_path, (10, 14), (15, 15))
    r = compare(c.a, c.b, realized, pol, ())
    assert r.declared_or_realized == 'REALIZED' and r.aggregation == 'mean_of_A_and_B'
    assert r.values[0] == (F(12), F(15)) and r.deltas[0] == F(1, 5)
    assert r.status == 'REVIEW_REQUIRED'  # both descriptors >= 0.20, but no D09 review
    # the favourable single action (b.A=15 vs a.B=14 -> 1/15) is never chosen; a smaller mean gap fails
    c, pol, realized, _ = _realized_setup(parameter_case, tmp_path, (12, 14), (15, 15))
    assert compare(c.a, c.b, realized, pol, ()).status == 'DIVERSITY_DEFICIT'


def test_asel2_realized_blocks_missing_or_unverified(require, parameter_case, tmp_path):
    from dataclasses import replace
    compare = require('m56.catalog', 'compare_realized')
    c, pol, realized, ref = _realized_setup(parameter_case, tmp_path, (10, 14), (15, 15))
    missing = {**realized, c.b.id: {k: {'A': v['A']} for k, v in realized[c.b.id].items()}}
    assert compare(c.a, c.b, missing, pol, ()).status == 'BLOCKED_COMPARABILITY'
    bad = replace(ref, sha256='0' * 64)
    tampered = {**realized, c.a.id: {k: {a: (v[a][0], bad) for a in 'AB'} for k, v in realized[c.a.id].items()}}
    assert compare(c.a, c.b, tampered, pol, ()).status == 'BLOCKED_COMPARABILITY'
    assert compare(c.a, c.b, realized, replace(c.policies, descriptor_specs={}), ()).status == 'BLOCKED_COMPARABILITY'
