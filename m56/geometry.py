"""Offline full-body geometry. No native queries; unproven bounds block compilation."""
from __future__ import annotations

from fractions import Fraction
from collections.abc import Mapping
from itertools import product
from math import sin, cos, radians, isfinite, sqrt, nextafter, inf, pi, acos
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from .model import (Candidate, QueryBundle, PolicyBundle, CompiledFixture, BlockedFixture,
                    BodyRecord, Transform6, VertexSet, Vec3, DirectedRoute, Number,
                    BoundCertificate, Sweep, CapabilityProof, ReviewRecord,
                    Section, decode_record, encode_record)
from .catalog import _digest, _review_binds


def _rotate(point: Vec3, pitch: float, yaw: float, roll: float) -> Vec3:
    cp,sp=cos(radians(pitch)),sin(radians(pitch))
    cy,sy=cos(radians(yaw)),sin(radians(yaw))
    cr,sr=cos(radians(roll)),sin(radians(roll))
    x,y,z=point
    # CARLA Transform.GetMatrix (left-handed Unreal basis), not generic right-handed Euler.
    return (cp*cy*x+(cy*sp*sr-sy*cr)*y+(-cy*sp*cr-sy*sr)*z,
            cp*sy*x+(sy*sp*sr+cy*cr)*y+(-sy*sp*cr+cy*sr)*z,
            sp*x-cp*sr*y+cp*cr*z)


_VERTEX_CACHE = {}


def world_vertices(body: BodyRecord, pose: Transform6) -> VertexSet:
    values=(*body.bbox_offset,*body.rotation,*body.extents,
            pose.x,pose.y,pose.z,pose.pitch,pose.yaw,pose.roll)
    # Pure in these 15 numbers: memoized so online per-tick detection does not rebuild old frames' bodies.
    # Keyed by repr so -0.0/0.0 and Fraction/float never alias. ponytail: bounded clear-all cache.
    key = tuple(map(repr, values))
    hit = _VERTEX_CACHE.get(key)
    if hit is not None:
        return hit
    if not all(isfinite(v) for v in values) or any(v<=0 for v in body.extents):
        raise ValueError('INVALID_BODY_TRANSFORM')
    result = _world_vertices(body, pose)
    if len(_VERTEX_CACHE) > 65536:
        _VERTEX_CACHE.clear()
    _VERTEX_CACHE[key] = result
    return result


def _world_vertices(body: BodyRecord, pose: Transform6) -> VertexSet:
    vertices=[]
    for signs in product((-1,1),repeat=3):
        local=_rotate(tuple(s*e for s,e in zip(signs,body.extents)),*body.rotation)
        translated=tuple(a+b for a,b in zip(local,body.bbox_offset))
        rotated=_rotate(translated,pose.pitch,pose.yaw,pose.roll)
        vertices.append(tuple(a+b for a,b in zip(rotated,(pose.x,pose.y,pose.z))))
    return tuple(vertices)


_PROJECTION_CACHE = {}


def project_route(point: Vec3, route: DirectedRoute) -> Number | BlockedFixture:
    # Pure in (point values, immutable route): memoized by value + route identity (strong ref kept) so online
    # per-tick detection does not re-project old frames. ponytail: bounded clear-all cache.
    try:
        key = (tuple(point), id(route))
    except TypeError:
        return _project_route(point, route)
    hit = _PROJECTION_CACHE.get(key)
    if hit is not None and hit[0] is route:
        return hit[1]
    if len(_PROJECTION_CACHE) > 65536:
        _PROJECTION_CACHE.clear()
    result = _project_route(point, route)
    _PROJECTION_CACHE[key] = (route, result)
    return result


def _project_route(point: Vec3, route: DirectedRoute) -> Number | BlockedFixture:
    if (len(point)!=3 or not all(isfinite(v) for v in point)
            or len(route.transforms)!=len(route.arc) or len(route.arc)<2
            or any(b<=a for a,b in zip(route.arc,route.arc[1:]))):
        return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
    # Rational arithmetic over the exact binary64 packets avoids an epsilon tie rescue.
    p=tuple(Fraction(v) for v in point)
    candidates=[]
    for i,(a,b) in enumerate(zip(route.transforms,route.transforms[1:])):
        if not all(isfinite(v) for v in (a.x,a.y,a.z,b.x,b.y,b.z)):
            return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
        start=tuple(Fraction(v) for v in (a.x,a.y,a.z))
        direction=tuple(Fraction(v)-u for v,u in zip((b.x,b.y,b.z),start))
        length2=sum(v*v for v in direction)
        if length2==0:
            return BlockedFixture(('DEGENERATE_ROUTE_SEGMENT',))
        u=max(Fraction(0),min(Fraction(1),sum((v-s)*d for v,s,d in zip(p,start,direction))/length2))
        projected=tuple(s+u*d for s,d in zip(start,direction))
        distance2=sum((v-q)**2 for v,q in zip(p,projected))
        arc=route.arc[i]+u*(route.arc[i+1]-route.arc[i])
        candidates.append((distance2,arc))
    minimum=min(d for d,_ in candidates)
    stations={s for d,s in candidates if d==minimum}
    if len(stations)!=1:
        return BlockedFixture(('NONUNIQUE_PROJECTION',))
    return stations.pop()


def _rotation_distance(a: Transform6, b: Transform6) -> float:
    columns_a=[_rotate(v,a.pitch,a.yaw,a.roll) for v in ((1,0,0),(0,1,0),(0,0,1))]
    columns_b=[_rotate(v,b.pitch,b.yaw,b.roll) for v in ((1,0,0),(0,1,0),(0,0,1))]
    trace=sum(sum(x*y for x,y in zip(u,v)) for u,v in zip(columns_a,columns_b))
    return acos(max(-1.,min(1.,(trace-1)/2)))


def swept_volume(route: DirectedRoute, body: BodyRecord,
                 certificates: tuple[BoundCertificate,...]) -> Sweep | BlockedFixture:
    if not certificates:
        return BlockedFixture(('CONTINUOUS_BOUND_MISSING',))
    if (len(route.transforms)!=len(route.arc) or len(route.arc)<2 or not route.continuity
            or any(b<=a for a,b in zip(route.arc,route.arc[1:]))):
        return BlockedFixture(('ROUTE_CONTINUITY_UNPROVEN',))
    volumes=[]; vertical=[]; selected=[]
    route_hash=_digest(route);body_hash=_digest(body)
    for i,(a,b) in enumerate(zip(route.transforms,route.transforms[1:])):
        interval=(route.arc[i],route.arc[i+1])
        xyz_a=(a.x,a.y,a.z);xyz_b=(b.x,b.y,b.z)
        if not all(isfinite(v) for v in (*xyz_a,*xyz_b)):
            return BlockedFixture(('INVALID_ROUTE_GEOMETRY',))
        chord2=sum((Fraction(q)-Fraction(p))**2 for p,q in zip(xyz_a,xyz_b))
        if interval[1]-interval[0]>Fraction(1,4) or chord2>Fraction(1,16):
            return BlockedFixture(('GEOMETRY_SAMPLE_SPACING',))
        matches=[c for c in certificates if c.interval==interval and
                 c.bounds.get('route_hash')==route_hash and c.bounds.get('body_hash')==body_hash]
        if len(matches)!=1:
            return BlockedFixture(('CONTINUOUS_BOUND_INVALID',))
        cert=matches[0]
        binding={name:getattr(cert,name) for name in ('method','interval','bounds','error','source')}
        if (cert.method!='bounded-pose-tube-v1' or cert.source.method!=cert.method
                or not _review_binds(cert.review,_digest(binding),('CONTINUOUS_BOUND',))
                or set(cert.bounds)!={'route_hash','body_hash','translation_deviation_m','rotation_from_start_rad'}
                or not Fraction(0)<cert.error<=Fraction(1,20)):
            return BlockedFixture(('CONTINUOUS_BOUND_INVALID',))
        displacement=cert.bounds['translation_deviation_m'];angle=cert.bounds['rotation_from_start_rad']
        if (isinstance(displacement,bool) or isinstance(angle,bool)
                or not isinstance(displacement,(Fraction,int)) or not isinstance(angle,(Fraction,int))
                or displacement<0 or angle<0 or displacement>Fraction(1,20)
                or float(angle)<_rotation_distance(a,b)):
            return BlockedFixture(('CONTINUOUS_BOUND_INVALID',))
        start_vertices=world_vertices(body,a)
        # Pose tube: all rotations stay within angle of start; translation stays within
        # displacement of endpoint chord. Radius includes bbox offset, not just extents.
        radius=max(sqrt(sum((v-p)**2 for v,p in zip(vertex,(a.x,a.y,a.z)))) for vertex in start_vertices)
        inflation=float(displacement)+2*radius*sin(min(float(angle),pi)/2)+float(cert.error)
        translated=[tuple(v+(q-p) for v,p,q in zip(vertex,(a.x,a.y,a.z),(b.x,b.y,b.z)))
                    for vertex in start_vertices]
        endpoints=(*start_vertices,*translated)
        low=tuple(nextafter(min(v[k] for v in endpoints)-inflation,-inf) for k in range(3))
        high=tuple(nextafter(max(v[k] for v in endpoints)+inflation,inf) for k in range(3))
        volumes.append(tuple(tuple(high[k] if sign[k] else low[k] for k in range(3))
                             for sign in product((0,1),repeat=3)))
        vertical.append((low[2],high[2]));selected.append(cert)
    return Sweep(tuple(volumes),tuple(selected),tuple(vertical))


def compile_fixture(candidate: Candidate, queries: QueryBundle,
                    policies: PolicyBundle) -> CompiledFixture | BlockedFixture:
    reasons=[];sweeps={}
    binding=_digest({'candidate':candidate,'policy':policies,'routes':queries.routes,
                     'bodies':queries.bodies,'poses':queries.poses,'map':queries.map,
                     'boot':queries.boot,'world':queries.world})
    for role in ('EGO','NPC'):
        if role not in queries.routes or role not in queries.bodies or role not in queries.poses:
            reasons.append('MATERIALIZATION_REQUIRED')
            continue
        sweep=swept_volume(queries.routes[role],queries.bodies[role],queries.certificates)
        if isinstance(sweep,BlockedFixture):
            reasons.extend(sweep.reasons)
        else:
            sweeps[role]=sweep
        ground=queries.ground.get(role)
        if ground is None or not _proof_valid(ground,'GROUND:'+role,binding):
            reasons.append('GROUND_UNKNOWN')
    needed={'RUNIN_ROOM':'RUNIN_ROOM_UNPROVEN','BODY_FIT':'BODY_FIT_UNPROVEN',
            'DESTINATION_ROOM':'DESTINATION_ROOM_UNPROVEN'}
    for kind,reason in needed.items():
        matches=[p for p in queries.capabilities if p.kind==kind]
        if len(matches)!=1 or not _proof_valid(matches[0],kind,binding):
            reasons.append(reason)
    if set(sweeps)=={'EGO','NPC'} and candidate.category in ('C','L','M'):
        intersections=_interaction_volumes(candidate.category,sweeps['EGO'],sweeps['NPC'],queries.capabilities,binding)
        if isinstance(intersections,BlockedFixture):
            reasons.extend(intersections.reasons)
        elif not intersections:
            reasons.append('NO_3D_CONFLICT')
        elif not _connected_boxes(intersections):
            reasons.append('DISCONNECTED_CONFLICT_REVIEW_REQUIRED')
    review_payload=queries.physics.get('fixture_review')
    materialized=queries.physics.get('fixture')
    compilation=queries.physics.get('compilation')
    if review_payload is None or (materialized is None and compilation is None):
        reasons.append('FIXTURE_REVIEW_REQUIRED')
    if reasons:
        return BlockedFixture(tuple(dict.fromkeys(reasons)))
    review=decode_record('ReviewRecord',encode_record(review_payload))
    if compilation is not None and materialized is not None:
        return BlockedFixture(('AMBIGUOUS_COMPILATION_INPUT',))
    if compilation is not None:
        fixture=_compile_packet(candidate,queries,policies,compilation,review)
        if isinstance(fixture,BlockedFixture):
            return fixture
    else:
        fixture=decode_record('CompiledFixture',encode_record(materialized))
    unsigned=replace(queries,physics={k:v for k,v in queries.physics.items() if k!='fixture_review'})
    envelope={'candidate':candidate,'queries':unsigned,'policy':policies}
    if (not isinstance(fixture,CompiledFixture) or not isinstance(review,ReviewRecord)
            or not _review_binds(review,_digest(envelope),('FIXTURE_COMPILE',))):
        return BlockedFixture(('FIXTURE_REVIEW_INVALID',))
    if (fixture.candidate_hash!=_digest(candidate) or fixture.policy_hash!=_digest(policies)
            or fixture.poses!=queries.poses or fixture.routes!=queries.routes
            or fixture.proofs!=queries.capabilities+tuple(queries.ground.values())
            or fixture.environment!=candidate.environment
            or fixture.freeze_ref!=review.authority_ref):
        return BlockedFixture(('MATERIALIZATION_BINDING_MISMATCH',))
    expected_actors=tuple(replace(a,pose=queries.poses[a.role],
                        destination=queries.routes[a.role].destination) for a in candidate.actors)
    if fixture.actors!=expected_actors:
        return BlockedFixture(('MATERIALIZATION_ACTOR_MISMATCH',))
    if candidate.category in ('C','L','M'):
        g=policies.approved_parameters.get(candidate.id+'.G')
        if g is None or g.units!='m' or g.values!=(fixture.G,) or candidate.parameters.get('G')!=g:
            return BlockedFixture(('G_POLICY_MISMATCH',))
    domain=fixture.domain
    if domain.hash!=_digest({k:getattr(domain,k) for k in
                            ('e_entry','e_exit','n_entry','n_exit','region','topology','proof')}):
        return BlockedFixture(('DOMAIN_HASH_MISMATCH',))
    if not domain.proof or not domain.topology or len(domain.region)<4:
        return BlockedFixture(('DOMAIN_TOPOLOGY_UNPROVEN',))
    if candidate.category=='M':
        from .catalog import _category_proven
        if not _category_proven(candidate,'M') or domain.topology.get('kind')!='branch-to-mainflow':
            return BlockedFixture(('M_CATEGORY_UNPROVEN',))
        merge=next(p for p in queries.capabilities if p.kind=='MERGE_TRANSITION')
        if set(domain.region)!=set(merge.limits['transition_region']):
            return BlockedFixture(('M_TRANSITION_REGION_MISMATCH',))
    # GEOS is planar only; vertical enclosure and finite sections are checked separately.
    from shapely.geometry import MultiPoint, Point
    region=MultiPoint([(v[0],v[1]) for v in domain.region]).convex_hull
    if region.geom_type!='Polygon' or region.is_empty or not region.is_valid:
        return BlockedFixture(('DOMAIN_INVALID',))
    zmin=min(v[2] for v in domain.region);zmax=max(v[2] for v in domain.region)
    if candidate.category in ('C','L','M'):
        for box in intersections:
            if any(not region.covers(Point(v[0],v[1])) or not zmin<=v[2]<=zmax for v in box):
                return BlockedFixture(('DOMAIN_DOES_NOT_ENCLOSE_SWEPT_CONFLICT',))
    for role,entry,exit in (('EGO',domain.e_entry,domain.e_exit),('NPC',domain.n_entry,domain.n_exit)):
        route=queries.routes[role]
        if not route.arc[0]<=entry.route_station<exit.route_station<route.arc[-1]:
            return BlockedFixture(('DOMAIN_SECTION_ORDER_INVALID',))
        for section in (entry,exit):
            if not _section_matches_route(section,route):
                return BlockedFixture(('DOMAIN_SECTION_INVALID',))
        if (not _on_domain_boundary(entry,domain.region,True)
                or not _on_domain_boundary(exit,domain.region,False)):
            return BlockedFixture(('DOMAIN_SECTION_BOUNDARY_MISMATCH',))
        if candidate.category in ('C','L','M') and (route.destination-exit.route_station<5
                                                    or route.arc[-1]-route.destination<5):
            return BlockedFixture(('DESTINATION_ROOM_UNPROVEN',))
    if candidate.category in ('C','L','M'):
        runin=next(p for p in queries.capabilities if p.kind=='RUNIN_ROOM')
        if runin.limits['G_m']!=fixture.G:
            return BlockedFixture(('RUNIN_G_MISMATCH',))
        stations=tuple(project_route(p,queries.routes['EGO']) for p in
                       world_vertices(queries.bodies['EGO'],queries.poses['EGO']))
        if any(isinstance(s,BlockedFixture) for s in stations):
            return BlockedFixture(('RUNIN_FRONT_PROJECTION_UNPROVEN',))
        front_distance=domain.e_entry.route_station-max(stations)
        if (front_distance-runin.uncertainty<=fixture.G
                or abs(front_distance-runin.limits['initial_front_m'])>runin.uncertainty):
            return BlockedFixture(('RUNIN_FRONT_GEOMETRY_MISMATCH',))
    return fixture


def _compile_packet(candidate, queries, policies, packet, review):
    """Materialize reviewed pre-outcome geometry data; no fixture needed for queries."""
    if (not isinstance(review,ReviewRecord) or not isinstance(packet,Mapping)
            or set(packet)!={'region','topology','proof','G','sections','responses','pair'}):
        return BlockedFixture(('COMPILATION_PACKET_INVALID',))
    # Use the common strict decoder at this untyped JSON-data seam.
    dummy=Section(((0.,0.,0.),(0.,1.,0.),(0.,0.,1.)),(1.,0.,0.),Fraction(0),{})
    raw={
        'candidate_hash':_digest(candidate),'policy_hash':_digest(policies),
        'actors':tuple(replace(a,pose=queries.poses[a.role],destination=queries.routes[a.role].destination)
                       for a in candidate.actors),
        'environment':candidate.environment,'poses':queries.poses,'routes':queries.routes,
        'domain':{'e_entry':dummy,'e_exit':dummy,'n_entry':dummy,'n_exit':dummy,
                  'region':packet['region'],'topology':packet['topology'],
                  'proof':packet['proof'],'hash':'0'*64},
        'G':packet['G'],'sections':packet['sections'],'responses':packet['responses'],'pair':packet['pair'],
        'proofs':queries.capabilities+tuple(queries.ground.values()),'freeze_ref':review.authority_ref,
    }
    fixture=decode_record('CompiledFixture',encode_record(raw))
    if not isinstance(fixture,CompiledFixture):
        return BlockedFixture(('COMPILATION_PACKET_INVALID',))
    domain=fixture.domain
    sections=[]
    for role in ('EGO','NPC'):
        derived=_derive_box_sections(queries.routes[role],domain.region)
        if isinstance(derived,BlockedFixture):
            return derived
        sections.extend(derived)
    topology={**domain.topology,'compiler':{'method':'box-route-clip-v1',
             'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
             'map':queries.map,'route_hashes':{role:_digest(route) for role,route in queries.routes.items()}}}
    domain=replace(domain,e_entry=sections[0],e_exit=sections[1],n_entry=sections[2],n_exit=sections[3],
                   topology=topology)
    domain=replace(domain,hash=_digest({k:getattr(domain,k) for k in
                   ('e_entry','e_exit','n_entry','n_exit','region','topology','proof')}))
    return replace(fixture,domain=domain)


def _derive_box_sections(route: DirectedRoute, region: VertexSet):
    """Exact slab clipping for a reviewed conservative prism, not a sampled crossing.

    Unsupported non-prismatic regions, boundary grazes or repeated crossings block;
    this routine never convexifies or expands a submitted region to rescue it.
    """
    if not region or any(not isfinite(v) for p in region for v in p):
        return BlockedFixture(('DOMAIN_INVALID',))
    low=tuple(min(Fraction(p[k]) for p in region) for k in range(3))
    high=tuple(max(Fraction(p[k]) for p in region) for k in range(3))
    if any(a>=b for a,b in zip(low,high)) or set(region)!=set(product(*zip(low,high))):
        return BlockedFixture(('DOMAIN_RECIPE_UNSUPPORTED',))
    hits=[]
    for i,(a,b) in enumerate(zip(route.transforms,route.transforms[1:])):
        start=tuple(Fraction(v) for v in (a.x,a.y,a.z))
        delta=tuple(Fraction(v)-p for v,p in zip((b.x,b.y,b.z),start))
        enter=Fraction(0);leave=Fraction(1)
        for k,d in enumerate(delta):
            if not d:
                if not low[k]<start[k]<high[k]:
                    enter=Fraction(2);break
            else:
                x,y=sorted(((low[k]-start[k])/d,(high[k]-start[k])/d))
                enter=max(enter,x);leave=min(leave,y)
        if enter>=leave:
            continue
        def endpoint(t):
            return (route.arc[i]+t*(route.arc[i+1]-route.arc[i]),
                    tuple(p+t*d for p,d in zip(start,delta)),delta)
        hits.append((endpoint(enter),endpoint(leave)))
    if not hits or any(a[1][0]!=b[0][0] for a,b in zip(hits,hits[1:])):
        return BlockedFixture(('DOMAIN_CROSSING_AMBIGUOUS',))
    ends=(hits[0][0],hits[-1][1])
    if ends[0][0]<=route.arc[0] or ends[1][0]>=route.arc[-1]:
        return BlockedFixture(('DOMAIN_CROSSING_UNBRACKETED',))
    sections=[]
    for station,point,direction in ends:
        faces=[k for k in range(3) if point[k] in (low[k],high[k]) and direction[k]]
        if len(faces)!=1:
            return BlockedFixture(('DOMAIN_CROSSING_AMBIGUOUS',))
        axis=faces[0]
        vertices=tuple(tuple(float(v) for v in p) for p in
                       product(*( (point[k],) if k==axis else (low[k],high[k]) for k in range(3))))
        normal=tuple(float(1 if direction[k]>0 else -1) if k==axis else 0. for k in range(3))
        sections.append(Section(vertices,normal,station,{'z_min':low[2],'z_max':high[2]}))
    return tuple(sections)


def _proof_valid(proof: CapabilityProof, kind: str, binding: str) -> bool:
    packet={key:getattr(proof,key) for key in ('kind','method','raw_refs','uncertainty','limits','status')}
    if (proof.kind!=kind or not proof.method or proof.status!='CORROBORATED'
            or not proof.raw_refs or not _exact_nonnegative(proof.uncertainty)
            or not 0<=proof.uncertainty<=Fraction(1,20)
            or proof.limits.get('materialization_hash')!=binding
            or not _review_binds(proof.review,_digest(packet),('CAPABILITY:'+kind,))):
        return False
    if kind=='MERGE_TRANSITION':
        region=proof.limits.get('transition_region')
        return (proof.method=='branch-to-mainflow-geometry-topology'
                and _is_box(region))
    # Bounds are measured recipe outputs. Include uncertainty in the adverse direction.
    required={
        'BODY_FIT':('minimum_road_edge_m','minimum_body_separation_m'),
        'RUNIN_ROOM':('required_m','available_m','initial_front_m','G_m'),
        'DESTINATION_ROOM':('exit_to_destination_m','destination_to_plan_end_m'),
        'GROUND':('maximum_ground_error_m',),
    }.get('GROUND' if kind.startswith('GROUND:') else kind)
    if required is None or any(not _exact_nonnegative(proof.limits.get(k)) for k in required):
        return False
    if kind=='BODY_FIT':
        return (proof.limits['minimum_road_edge_m']-proof.uncertainty>=Fraction(3,20)
                and proof.limits['minimum_body_separation_m']-proof.uncertainty>=Fraction(1,5))
    if kind=='RUNIN_ROOM':
        return (proof.limits.get('required_m',0)>0 and
                proof.limits.get('available_m',-1)>=proof.limits['required_m'] and
                proof.limits.get('initial_front_m',-1)>proof.limits.get('G_m',inf))
    if kind=='DESTINATION_ROOM':
        return (proof.limits.get('exit_to_destination_m',-1)>=5 and
                proof.limits.get('destination_to_plan_end_m',-1)>=5)
    if kind.startswith('GROUND:'):
        return (proof.limits['maximum_ground_error_m']+proof.uncertainty<=Fraction(1,20)
                and isinstance(proof.limits.get('contact_method'),str)
                and bool(proof.limits['contact_method'].strip()))
    return False


def _exact_nonnegative(value) -> bool:
    return not isinstance(value,bool) and isinstance(value,(Fraction,int)) and value>=0


def _on_domain_boundary(section, region: VertexSet, entry: bool) -> bool:
    length=sqrt(sum(v*v for v in section.normal))
    distances=[sum((v-o)*n for v,o,n in zip(p,section.vertices[0],section.normal))/length
               for p in region]
    # Nonzero plane extent was already checked by _section_matches_route.
    extremum=min(distances) if entry else max(distances)
    return abs(extremum)<=float(Fraction(1,20))


def _is_box(region) -> bool:
    if not isinstance(region,tuple) or len(region)!=8:
        return False
    if any(not isinstance(p,tuple) or len(p)!=3 or
           any(isinstance(v,bool) or not isinstance(v,(int,float,Fraction)) or not isfinite(v) for v in p)
           for p in region):
        return False
    low=tuple(min(p[k] for p in region) for k in range(3))
    high=tuple(max(p[k] for p in region) for k in range(3))
    return all(a<b for a,b in zip(low,high)) and set(region)==set(product(*zip(low,high)))


def _interaction_volumes(category, ego, npc, capabilities, binding):
    overlap=_overlaps(ego,npc)
    if category!='M':
        return overlap
    matches=[p for p in capabilities if p.kind=='MERGE_TRANSITION']
    if len(matches)!=1 or not _proof_valid(matches[0],'MERGE_TRANSITION',binding):
        return BlockedFixture(('M_TRANSITION_UNPROVEN',))
    region=matches[0].limits['transition_region']
    return _overlaps(Sweep(overlap,(),()),Sweep((region,),(),()))


def _overlaps(a: Sweep, b: Sweep) -> tuple[VertexSet,...]:
    intersections=[]
    for left in a.volumes:
        for right in b.volumes:
            low=tuple(max(min(p[k] for p in left),min(p[k] for p in right)) for k in range(3))
            high=tuple(min(max(p[k] for p in left),max(p[k] for p in right)) for k in range(3))
            if all(x<y for x,y in zip(low,high)):
                intersections.append(tuple(tuple(high[k] if sign[k] else low[k] for k in range(3))
                                    for sign in product((0,1),repeat=3)))
    return tuple(intersections)


def _connected_boxes(boxes: tuple[VertexSet,...]) -> bool:
    if not boxes:
        return False
    extents=[(tuple(min(p[k] for p in box) for k in range(3)),
              tuple(max(p[k] for p in box) for k in range(3))) for box in boxes]
    remaining=set(range(1,len(boxes)));queue=[0]
    while queue:
        i=queue.pop()
        neighbors=[j for j in remaining if all(extents[i][0][k]<=extents[j][1][k] and
                    extents[j][0][k]<=extents[i][1][k] for k in range(3))]
        remaining.difference_update(neighbors);queue.extend(neighbors)
    return not remaining


def _section_matches_route(section, route: DirectedRoute) -> bool:
    if (len(set(section.vertices))<3 or not all(isfinite(v) for p in section.vertices for v in p)
            or not all(isfinite(v) for v in section.normal)):
        return False
    length=sqrt(sum(v*v for v in section.normal))
    if length==0:
        return False
    normal=tuple(v/length for v in section.normal)
    first=section.vertices[0]
    # Fixed spec geometry budget; not an epsilon for diversity or event holds.
    error=float(Fraction(1,20))
    if any(abs(sum((v-o)*n for v,o,n in zip(point,first,normal)))>error for point in section.vertices):
        return False
    for i,(a,b) in enumerate(zip(route.arc,route.arc[1:])):
        if a<=section.route_station<=b:
            start=route.transforms[i];end=route.transforms[i+1]
            direction=(end.x-start.x,end.y-start.y,end.z-start.z)
            if sum(x*y for x,y in zip(direction,normal))<=0:
                return False
            u=float((section.route_station-a)/(b-a))
            point=tuple(s+u*d for s,d in zip((start.x,start.y,start.z),direction))
            if abs(sum((v-o)*n for v,o,n in zip(point,first,normal)))>error:
                return False
            # Section must have area and contain route point in its own plane.
            from shapely.geometry import MultiPoint,Point
            dropped=max(range(3),key=lambda k:abs(normal[k]))
            axes=[k for k in range(3) if k!=dropped]
            polygon=MultiPoint([(p[axes[0]],p[axes[1]]) for p in section.vertices]).convex_hull
            return polygon.geom_type=='Polygon' and polygon.covers(Point(point[axes[0]],point[axes[1]]))
    return False
