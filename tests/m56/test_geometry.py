"""Synthetic geometry contracts; no CARLA queries/fixture admission."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.fixture
def geometry_case():
    from types import SimpleNamespace
    from m56.model import (SourceRef,BodyRecord,Transform6,DirectedRoute,QueryBundle,
                           Candidate,ActorRecipe,PolicyBundle)
    ref=SourceRef('synthetic://geometry','a'*64,1,'test','literal','SYNTHETIC_TEST')
    body=BodyRecord((1.,0.,0.),(0.,90.,0.),(2.,1.,.5),(),
                    'vehicle.audi.a2',{}, {},ref)
    route=DirectedRoute((),(Transform6(0,0,0,0,0,0),Transform6(.25,0,0,0,0,0)),
                        (F(0),F(1,4)),'b'*64,(ref,),F(1,4))
    poses={'EGO':Transform6(0,0,0,0,0,0),'NPC':Transform6(0,0,0,0,0,0)}
    queries=QueryBundle('SYNTHETIC_BOOT','SYNTHETIC_WORLD',{'hash':'b'*64},
        {'EGO':route,'NPC':route},{'EGO':body,'NPC':body},poses,{}, {},(),(),(ref,))
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,
                   {'kind':'SYNTHETIC_TEST'},{'kind':'SYNTHETIC_TEST'},F(10))
                 for role,pose in poses.items())
    candidate=Candidate('C01','C01','test',(),'C','Town04','SYNTHETIC_SITE',actors,
                         {},(),{'weather':{},'light':{}},(ref,))
    policies=PolicyBundle('test','c'*64,{}, {},{},(ref,))
    return SimpleNamespace(body=body,route=route,queries=queries,candidate=candidate,
                           policies=policies,ref=ref)


def test_rear_body_and_sweep_required(require,geometry_case):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    out=compile(c.candidate,c.queries,c.policies)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'CONTINUOUS_BOUND_MISSING' in out.reasons
    # A downstream actor center is not whole-body exit proof.
    vertices=require('m56.geometry','world_vertices')
    pose=replace(c.queries.poses['NPC'],x=1.)
    body=replace(c.body,bbox_offset=(-1.,0.,0.))
    assert pose.x>F(1,2)
    assert min(v[0] for v in vertices(body,pose))<F(1,2)


def test_bbox_offset_rotation_not_origin_extent(require,geometry_case):
    vertices=require('m56.geometry','world_vertices')
    from m56.model import Transform6
    out=vertices(geometry_case.body,Transform6(10,0,0,0,0,0))
    assert min(v[0] for v in out)==10
    assert max(v[0] for v in out)==12
    assert min(v[1] for v in out)==-2
    assert max(v[2] for v in out)==.5


def test_pitch_roll_and_actor_rotation_transform_bbox_offset(require,geometry_case):
    vertices=require('m56.geometry','world_vertices')
    from m56.model import Transform6
    body=replace(geometry_case.body,bbox_offset=(2.,0.,0.),rotation=(0.,0.,0.),
                  extents=(1.,2.,3.))
    out=vertices(body,Transform6(10,20,30,90,0,90))
    # CARLA left-handed pitch/roll matrix: actor-local x -> +z,
    # y -> +x and z -> +y at pitch=roll=90deg.
    assert sorted({round(v[0],12) for v in out})==[8,12]
    assert sorted({round(v[1],12) for v in out})==[17,23]
    assert sorted({round(v[2],12) for v in out})==[31,33]


def test_nonunique_projection_invalid(require,geometry_case):
    project=require('m56.geometry','project_route')
    from m56.model import Transform6
    route=replace(geometry_case.route,transforms=tuple(Transform6(x,y,0,0,0,0)
                   for x,y in ((0,0),(1,0),(1,1),(0,1))),arc=(F(0),F(1),F(2),F(3)))
    out=project((.5,.5,0),route)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'NONUNIQUE_PROJECTION' in out.reasons


def test_unique_projection_returns_directed_arc_and_accepts_shared_vertex(require,geometry_case):
    project=require('m56.geometry','project_route')
    from m56.model import Transform6
    route=replace(geometry_case.route,transforms=tuple(Transform6(x,0,0,0,0,0)
                   for x in (2,1,0)),arc=(F(0),F(1),F(2)))
    assert project((1.5,.2,0),route)==F(1,2)
    assert project((1,0,0),route)==1


@pytest.fixture
def certified_segment(geometry_case):
    from m56.model import BoundCertificate,ReviewRecord,encode_record
    import hashlib,json
    def digest(value):
        return hashlib.sha256(json.dumps(encode_record(value),sort_keys=True,
                    separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    def make(route=None,body=None,**changes):
        c=geometry_case
        route=route or c.route;body=body or c.body
        source=replace(c.ref,method='bounded-pose-tube-v1')
        bounds={'route_hash':digest(route),'body_hash':digest(body),
                'translation_deviation_m':F(0),'rotation_from_start_rad':F(0)}
        bounds.update(changes)
        payload={'method':'bounded-pose-tube-v1','interval':(route.arc[0],route.arc[1]),
                 'bounds':bounds,'error':F(1,1000),'source':source}
        review=ReviewRecord(digest(payload),'CONTINUOUS_BOUND',(source,),
              'SYNTHETIC_TEST','2026-10-08','APPROVED',('analytic straight translation fixture',),source)
        return BoundCertificate(**payload,review=review)
    return make


def test_swept_volume_requires_review_bound_to_route_body_interval(require,geometry_case,certified_segment):
    sweep=require('m56.geometry','swept_volume')
    c=geometry_case
    certificate=certified_segment()
    out=sweep(c.route,c.body,(certificate,))
    assert len(out.volumes)==1
    xs=[p[0] for p in out.volumes[0]]
    assert min(xs)<0 and max(xs)>2.25
    assert out.vertical_limits[0][0]<-.5
    tampered=replace(certificate,bounds={**certificate.bounds,'translation_deviation_m':F(1)})
    blocked=sweep(c.route,c.body,(tampered,))
    assert blocked.status=='BLOCKED_FIXTURE'
    assert 'CONTINUOUS_BOUND_INVALID' in blocked.reasons


def test_sampled_endpoints_without_bound_never_certify(require,geometry_case):
    sweep=require('m56.geometry','swept_volume')
    c=geometry_case
    assert sweep(c.route,c.body,()).status=='BLOCKED_FIXTURE'


def test_certificate_does_not_cover_wrong_body_or_large_sample_gap(require,geometry_case,certified_segment):
    sweep=require('m56.geometry','swept_volume')
    c=geometry_case
    wrong=replace(c.body,extents=(2.,2.,1.))
    assert sweep(c.route,wrong,(certified_segment(),)).status=='BLOCKED_FIXTURE'
    from m56.model import Transform6
    long=replace(c.route,transforms=(c.route.transforms[0],Transform6(1,0,0,0,0,0)),arc=(F(0),F(1)))
    assert sweep(long,c.body,(certified_segment(long),)).status=='BLOCKED_FIXTURE'


def test_overpass_is_not_conflict(require,geometry_case,certified_segment):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    raised=replace(c.route,transforms=tuple(replace(t,z=5.) for t in c.route.transforms))
    q=replace(c.queries,routes={'EGO':c.route,'NPC':raised},
              certificates=(certified_segment(),certified_segment(raised)))
    out=compile(c.candidate,q,c.policies)
    assert 'NO_3D_CONFLICT' in out.reasons


def test_upstream_room_not_road_length(require,geometry_case):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    for scene in ('C06','L05','M01','C08'):
        out=compile(replace(c.candidate,id=scene),c.queries,c.policies)
        assert 'RUNIN_ROOM_UNPROVEN' in out.reasons


def test_ground_unknown_blocks_spawn(require,geometry_case):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    out=compile(c.candidate,c.queries,c.policies)
    assert 'GROUND_UNKNOWN' in out.reasons


def test_body_taper_fit_blocks(require,geometry_case):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    out=compile(c.candidate,replace(c.queries,physics={'lane_width_m':F(1)}),c.policies)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'BODY_FIT_UNPROVEN' in out.reasons


def test_destination_plus_plan_tail(require,geometry_case):
    compile=require('m56.geometry','compile_fixture')
    c=geometry_case
    # Even apparent8m outgoing room cannot stand for required5m destination+5m tail.
    out=compile(c.candidate,replace(c.queries,physics={'outgoing_room_m':F(8)}),c.policies)
    assert 'DESTINATION_ROOM_UNPROVEN' in out.reasons


@pytest.fixture
def materialization_case(geometry_case):
    from m56.model import (Transform6,DirectedRoute,Domain,Section,BoundCertificate,
        ReviewRecord,CapabilityProof,CompiledFixture,FrozenMetricPair,FrozenResponse,encode_record)
    import hashlib,json
    def digest(value):
        return hashlib.sha256(json.dumps(encode_record(value),sort_keys=True,separators=(',',':'),
                         ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    c=geometry_case
    from m56.model import ParameterProposal
    g=ParameterProposal('G',(F(3),),'m','synthetic-only bound',(c.ref,),'APPROVED_PROPOSAL_NOT_READY')
    c.candidate=replace(c.candidate,parameters={'G':g})
    c.policies=replace(c.policies,approved_parameters={'C01.G':g})
    body=replace(c.body,bbox_offset=(0.,0.,0.),rotation=(0.,0.,0.),extents=(.5,.25,.25))
    e=DirectedRoute((),tuple(Transform6(i/4-10,0,0,0,0,0) for i in range(85)),
                    tuple(F(i,4) for i in range(85)),'b'*64,(c.ref,),F(16))
    n=replace(e,transforms=tuple(Transform6(0,i/4-10,0,0,90,0) for i in range(85)))
    routes={'EGO':e,'NPC':n};poses={role:r.transforms[0] for role,r in routes.items()}
    def review(value,scope):
        return ReviewRecord(digest(value),scope,(c.ref,),'SYNTHETIC_TEST','2026-10-08',
                            'APPROVED',('synthetic analytic observation packet',),c.ref)
    certificates=[]
    for route in (e,n):
        for a,b in zip(route.arc,route.arc[1:]):
            packet={'method':'bounded-pose-tube-v1','interval':(a,b),
                    'bounds':{'route_hash':digest(route),'body_hash':digest(body),
                              'translation_deviation_m':F(0),'rotation_from_start_rad':F(0)},
                    'error':F(1,1000),'source':replace(c.ref,method='bounded-pose-tube-v1')}
            certificates.append(BoundCertificate(**packet,review=review(packet,'CONTINUOUS_BOUND')))
    q=replace(c.queries,routes=routes,bodies={'EGO':body,'NPC':body},poses=poses,
              certificates=tuple(certificates))
    binding=digest({'candidate':c.candidate,'policy':c.policies,'routes':routes,'bodies':q.bodies,
                    'poses':poses,'map':q.map,'boot':q.boot,'world':q.world})
    def proof(kind,limits):
        packet={'kind':kind,'method':'synthetic-analytic-proof','raw_refs':(c.ref,),
                'uncertainty':F(1,1000),'limits':{'materialization_hash':binding,**limits},
                'status':'CORROBORATED'}
        return CapabilityProof(**packet,review=review(packet,'CAPABILITY:'+kind))
    ground={role:proof('GROUND:'+role,{'maximum_ground_error_m':F(0),'contact_method':'synthetic-plane'})
            for role in ('EGO','NPC')}
    capabilities=(proof('BODY_FIT',{'minimum_road_edge_m':F(1),'minimum_body_separation_m':F(1)}),
        proof('RUNIN_ROOM',{'required_m':F(3),'available_m':F(9),'initial_front_m':F(17,2),'G_m':F(3)}),
        proof('DESTINATION_ROOM',{'exit_to_destination_m':F(5),'destination_to_plan_end_m':F(5)}))
    # Finite, reviewed conservative conflict region; no sampled-only witness.
    region=tuple((x,y,z) for x in (-1.,1.) for y in (-1.,1.) for z in (-1.,1.))
    def section(station,role):
        x=station-10
        vertices=tuple((x,y,z) if role=='EGO' else (y,x,z) for y in (-1.,1.) for z in (-1.,1.))
        return Section(vertices,(1.,0.,0.) if role=='EGO' else (0.,1.,0.),F(station),
                       {'z_min':F(-1),'z_max':F(1)})
    domain=Domain(section(9,'EGO'),section(11,'EGO'),section(9,'NPC'),section(11,'NPC'),
                  region,{'kind':'straight-crossing'},(c.ref,),'d'*64)
    domain=replace(domain,hash=digest({k:getattr(domain,k) for k in
        ('e_entry','e_exit','n_entry','n_exit','region','topology','proof')}))
    pair=FrozenMetricPair(('d_yield_m','t_entry_s'),('m','s'),('forward_distance','elapsed'),
             (('TRIGGER','CLEAR_N_CONFIRMED'),('TRIGGER','E_ENTRY')),'frozen-route','e'*64,'APPROVED_PROPOSAL_NOT_READY')
    responses=tuple(FrozenResponse('EGO',a,e,{'nominal':F(4)},{},{'trigger':'TRIGGER'},'f'*64) for a in ('A','B'))
    actors=tuple(replace(a,pose=poses[a.role],destination=routes[a.role].destination) for a in c.candidate.actors)
    fixture=CompiledFixture(digest(c.candidate),digest(c.policies),actors,c.candidate.environment,
           poses,routes,domain,F(3),{},responses,pair,capabilities+tuple(ground.values()),c.ref)
    q=replace(q,ground=ground,capabilities=capabilities,physics={'fixture':encode_record(fixture)})
    envelope={'candidate':c.candidate,'queries':q,'policy':c.policies}
    q=replace(q,physics={**q.physics,'fixture_review':encode_record(review(envelope,'FIXTURE_COMPILE'))})
    def resign(fixture=fixture, queries=q):
        unsigned=replace(queries,physics={'fixture':encode_record(fixture)})
        envelope={'candidate':c.candidate,'queries':unsigned,'policy':c.policies}
        return replace(unsigned,physics={**unsigned.physics,
                       'fixture_review':encode_record(review(envelope,'FIXTURE_COMPILE'))})
    c.queries=q;c.fixture=fixture;c.resign=resign;c.review=review;c.digest=digest
    return c


def test_reviewed_materialization_compiles_without_granting_runtime_authority(require,materialization_case):
    compile=require('m56.geometry','compile_fixture')
    from m56.model import CompiledFixture
    c=materialization_case;q=c.queries
    out=compile(c.candidate,q,c.policies)
    assert isinstance(out,CompiledFixture),out
    assert out.poses['EGO'].x==-10
    assert out.freeze_ref.kind=='SYNTHETIC_TEST'
    assert c.candidate.actors[0].pose.x==0  # original C0 recipe not mutated
    changed=replace(q,poses={**q.poses,'EGO':replace(q.poses['EGO'],x=-9.)})
    assert compile(c.candidate,changed,c.policies).status=='BLOCKED_FIXTURE'


def test_compilation_derives_sections_without_preexisting_fixture(require,materialization_case):
    compile=require('m56.geometry','compile_fixture')
    from m56.model import CompiledFixture,encode_record
    c=materialization_case;f=c.fixture
    packet={'region':f.domain.region,'topology':f.domain.topology,'proof':f.domain.proof,
            'G':f.G,'sections':f.sections,'responses':f.responses,'pair':f.pair}
    q=replace(c.queries,physics={'compilation':encode_record(packet)})
    envelope={'candidate':c.candidate,'queries':q,'policy':c.policies}
    q=replace(q,physics={**q.physics,'fixture_review':encode_record(c.review(envelope,'FIXTURE_COMPILE'))})
    out=compile(c.candidate,q,c.policies)
    assert isinstance(out,CompiledFixture),out
    assert out.domain.e_entry.route_station==9
    assert out.domain.e_exit.route_station==11
    assert out.domain.e_entry.normal==(1.,0.,0.)
    assert {v[0] for v in out.domain.e_entry.vertices}=={-1.}
    assert out.domain.n_entry.route_station==9
    assert out.domain.n_exit.route_station==11
    assert out.domain.n_exit.normal==(0.,1.,0.)
    assert len(out.domain.hash)==64
    import hashlib
    from pathlib import Path
    import m56.geometry as geometry
    assert out.domain.topology['compiler']['source_sha256']==hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest()
    assert 'fixture' not in q.physics  # no circular preparation prerequisite


@pytest.mark.parametrize('shape', ['nonprism','repeated','unbracketed','corner'])
def test_domain_derivation_never_rescues_unsupported_crossings(require,shape):
    derive=require('m56.geometry','_derive_box_sections')
    from itertools import product
    from m56.model import DirectedRoute,Transform6,BlockedFixture
    region=tuple(product((-1.,1.),(-1.,1.),(-1.,1.)))
    points={'nonprism':((-2.,0.),(2.,0.)),
            'repeated':((-2.,0.),(2.,0.),(-2.,0.)),
            'unbracketed':((0.,0.),(2.,0.)),
            'corner':((-2.,-2.),(2.,2.))}[shape]
    if shape=='nonprism':
        region=region[:-1]
    route=DirectedRoute((),tuple(Transform6(x,y,0.,0.,0.,0.) for x,y in points),
                        tuple(F(i*4) for i in range(len(points))),'b'*64,(),F(4))
    assert isinstance(derive(route,region),BlockedFixture)


@pytest.mark.parametrize('payload',[True,42,'unverified'])
def test_malformed_compilation_packet_blocks_instead_of_crashing(require,materialization_case,payload):
    compile=require('m56.geometry','compile_fixture')
    from m56.model import BlockedFixture,encode_record
    c=materialization_case
    q=replace(c.queries,physics={'compilation':payload})
    review=c.review({'candidate':c.candidate,'queries':q,'policy':c.policies},'FIXTURE_COMPILE')
    q=replace(q,physics={**q.physics,'fixture_review':encode_record(review)})
    assert isinstance(compile(c.candidate,q,c.policies),BlockedFixture)


def test_review_cannot_substitute_runin_marker(require,materialization_case):
    compile=require('m56.geometry','compile_fixture')
    c=materialization_case;old=c.queries.capabilities[1]
    changed=replace(old,limits={**old.limits,'G_m':F(1)})
    payload={k:getattr(changed,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    changed=replace(changed,review=c.review(payload,'CAPABILITY:RUNIN_ROOM'))
    capabilities=tuple(changed if p.kind=='RUNIN_ROOM' else p for p in c.queries.capabilities)
    q=replace(c.queries,capabilities=capabilities)
    fixture=replace(c.fixture,proofs=capabilities+tuple(q.ground.values()))
    out=compile(c.candidate,c.resign(fixture,q),c.policies)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'RUNIN_G_MISMATCH' in out.reasons


def test_rear_body_blocks_unfounded_spawn_front_distance(require,materialization_case):
    compile=require('m56.geometry','compile_fixture')
    c=materialization_case;old=c.queries.capabilities[1]
    changed=replace(old,limits={**old.limits,'initial_front_m':F(9)})
    payload={k:getattr(changed,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    changed=replace(changed,review=c.review(payload,'CAPABILITY:RUNIN_ROOM'))
    capabilities=tuple(changed if p.kind=='RUNIN_ROOM' else p for p in c.queries.capabilities)
    q=replace(c.queries,capabilities=capabilities)
    fixture=replace(c.fixture,proofs=capabilities+tuple(q.ground.values()))
    out=compile(c.candidate,c.resign(fixture,q),c.policies)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'RUNIN_FRONT_GEOMETRY_MISMATCH' in out.reasons


def test_disconnected_3d_conflicts_need_review_not_convex_bridge(require):
    connected=require('m56.geometry','_connected_boxes')
    from itertools import product
    first=tuple(product((0.,1.),(0.,1.),(0.,1.)))
    upper=tuple(product((0.,1.),(0.,1.),(5.,6.)))
    adjacent=tuple(product((1.,2.),(0.,1.),(0.,1.)))
    assert connected((first,upper)) is False
    assert connected((first,adjacent)) is True


def test_merge_domain_uses_reviewed_transition_not_whole_common_lane(require,materialization_case):
    interaction=require('m56.geometry','_interaction_volumes')
    from m56.model import Sweep,CapabilityProof,BlockedFixture
    from itertools import product
    c=materialization_case
    transition=tuple(product((-1.,1.),(-1.,1.),(-1.,1.)))
    common=tuple(product((1.,20.),(-1.,1.),(-1.,1.)))
    sweep=Sweep((transition,common),(),((-1.,1.),(-1.,1.)))
    packet={'kind':'MERGE_TRANSITION','method':'branch-to-mainflow-geometry-topology',
            'raw_refs':(c.ref,),'uncertainty':F(1,1000),
            'limits':{'materialization_hash':'b'*64,'transition_region':transition},'status':'CORROBORATED'}
    proof=CapabilityProof(**packet,review=c.review(packet,'CAPABILITY:MERGE_TRANSITION'))
    out=interaction('M',sweep,sweep,(proof,),'b'*64)
    assert not isinstance(out,BlockedFixture),out
    assert min(p[0] for box in out for p in box)==-1
    assert max(p[0] for box in out for p in box)==1  # not common-lane end20
    assert isinstance(interaction('M',sweep,sweep,(),'b'*64),BlockedFixture)
    assert isinstance(interaction('M',sweep,sweep,(proof,),'c'*64),BlockedFixture)


def test_section_normal_station_and_plane_are_correlated(require,geometry_case):
    valid=require('m56.geometry','_section_matches_route')
    from m56.model import Section
    route=geometry_case.route
    section=Section(((.125,-1.,-1.),(.125,1.,-1.),(.125,1.,1.),(.125,-1.,1.)),
                     (1.,0.,0.),F(1,8),{'z_min':F(-1),'z_max':F(1)})
    assert valid(section,route) is True
    assert valid(replace(section,normal=(-1.,0.,0.)),route) is False
    assert valid(replace(section,route_station=F(0)),route) is False
    assert valid(replace(section,vertices=((1.,0.,0.),)*4),route) is False


def test_signed_review_cannot_move_sections_off_domain_boundary(require,materialization_case):
    compile=require('m56.geometry','compile_fixture')
    c=materialization_case;domain=c.fixture.domain
    moved=replace(domain.e_entry,route_station=F(8),
                  vertices=tuple((-2.,y,z) for _,y,z in domain.e_entry.vertices))
    domain=replace(domain,e_entry=moved)
    domain=replace(domain,hash=c.digest({k:getattr(domain,k) for k in
        ('e_entry','e_exit','n_entry','n_exit','region','topology','proof')}))
    out=compile(c.candidate,c.resign(replace(c.fixture,domain=domain)),c.policies)
    assert out.status=='BLOCKED_FIXTURE'
    assert 'DOMAIN_SECTION_BOUNDARY_MISMATCH' in out.reasons


@pytest.mark.parametrize('kind,limits',[
    ('BODY_FIT',{'minimum_road_edge_m':F(3,20),'minimum_body_separation_m':F(1)}),
    ('GROUND:EGO',{'maximum_ground_error_m':F(1,20),'contact_method':'synthetic-plane'}),
    ('BODY_FIT',{'minimum_road_edge_m':True,'minimum_body_separation_m':F(1)}),
    ('GROUND:EGO',{'maximum_ground_error_m':'unknown','contact_method':'synthetic-plane'}),
])
def test_proof_bounds_include_uncertainty_and_reject_nonnumbers(require,materialization_case,kind,limits):
    valid=require('m56.geometry','_proof_valid')
    from m56.model import CapabilityProof
    c=materialization_case
    binding=c.queries.capabilities[0].limits['materialization_hash']
    packet={'kind':kind,'method':'synthetic-analytic-proof','raw_refs':(c.ref,),
            'uncertainty':F(1,1000),'limits':{'materialization_hash':binding,**limits},
            'status':'CORROBORATED'}
    proof=CapabilityProof(**packet,review=c.review(packet,'CAPABILITY:'+kind))
    assert valid(proof,kind,binding) is False


def test_forged_arc_cannot_hide_large_spatial_sampling_gap(require,geometry_case,certified_segment):
    sweep=require('m56.geometry','swept_volume')
    c=geometry_case
    route=replace(c.route,transforms=(c.route.transforms[0],replace(c.route.transforms[1],x=10.)))
    out=sweep(route,c.body,(certified_segment(route),))
    assert out.status=='BLOCKED_FIXTURE'
    assert 'GEOMETRY_SAMPLE_SPACING' in out.reasons


def test_vertex_memo_never_aliases_equal_but_distinct_inputs(require,geometry_case):
    vertices=require('m56.geometry','world_vertices')
    from m56.geometry import _world_vertices
    from m56.model import Transform6
    poses=(Transform6(10,0,0,0,0.,0),Transform6(10,0,0,0,-0.,0),Transform6(F(1,2),0,0,0,0,0),Transform6(.5,0,0,0,0,0))
    for pose in poses*2:  # second pass is served from the memo
        out=vertices(geometry_case.body,pose)
        assert repr(out)==repr(_world_vertices(geometry_case.body,pose)),pose
