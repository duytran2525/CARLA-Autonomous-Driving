"""G4 evidence kit for M56 runtime-recipe v2 (prereg d1c91ac + errata 737acbc/E5). NOT part of the m56 product.

The runner never reviews. This kit is the external producer/reviewer that OwnedCarlaBackend.bind(kit=...) calls:
  frame(...)                  per tick: native ground_projection witness per actor + metric context
  initialization_recipe(...)  recorded-initialization-v1 recipe source
  finish(...)                 W01 / INITIALIZATION reviews, COLLISION_DELIVERY, CONTINUOUS_CONTACT, CONTINUOUS_MOTION
Every review is CLAUDE_REVIEW_UNDER_DUY_DELEGATION (addendum A-G45): not independent, never Duy's own.
Bounds are conservative: a quantity that cannot be bounded is reported as a failing number, never rescued.
"""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import hashlib, json, math, os
V6 = os.environ.get('M56_RECIPE', 'v5') == 'v6'  # same switch as native_v2_common (prereg v6)

from m56.catalog import _digest
from m56.evidence import append_record
from m56.geometry import world_vertices
from m56.model import CapabilityProof, ReviewRecord, SourceRef

REVIEWER = 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION'
DATE = '2026-10-23'
UNC = Fraction(1, 1000)


def q(x):
    """Exact rational of a measured float, rounded DOWN for margins (conservative), 1e-4 m grid."""
    return Fraction(math.floor(x * 10000), 10000)


def q_up(x):
    return Fraction(math.ceil(x * 10000), 10000)


def ref_of(path, kind, method='claude-g4'):
    data = Path(path).read_bytes()
    return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', method, kind)


class Kit:
    def __init__(self, authority: SourceRef, fixture, drivable, qualification: SourceRef, tag: str):
        """authority: Duy-delegation receipt; drivable: shapely geometry of the CARLA driving-lane union (+ its source
        ref); qualification: native g4 probe output (collision fence observation)."""
        self.authority, self.fixture, self.tag = authority, fixture, tag
        self.drivable, self.drivable_ref = drivable
        self.boundary = self.drivable.boundary
        self.qualification = qualification
        self.fixture_hash = _digest(fixture)
        self.recipes = {}

    # -- reviews ---------------------------------------------------------------------------------------------
    def review(self, payload, scope, refs, reasons):
        return ReviewRecord(_digest(payload), scope, tuple(dict.fromkeys(refs)), REVIEWER, DATE, 'APPROVED',
                            tuple(reasons), self.authority)

    def proof(self, kind, method, raw, uncertainty, limits, refs, reasons):
        packet = dict(kind=kind, method=method, raw_refs=tuple(raw), uncertainty=uncertainty, limits=limits,
                      status='CORROBORATED')
        return CapabilityProof(**packet, review=self.review(packet, 'CAPABILITY:' + kind, (*raw, *refs), reasons))

    def _recipe(self, backend, name, payload):
        if name not in self.recipes:
            self.recipes[name] = backend._raw(f'g4/recipe-{name}.json', payload)
        return self.recipes[name]

    # -- per frame -------------------------------------------------------------------------------------------
    def frame(self, backend, frame_id, simtime, actors):
        import carla
        recipe = self._recipe(backend, 'ground', {
            'method': 'recorded-ground-contact-v1', 'version': '1',
            'limitations': 'world.ground_projection at the four body-bottom corners (bbox through actor pose); '
                           'error = max |corner z - projected ground z|; no wheel-contact getter exists (spec 5.4)'})
        out = []
        for a in actors:
            corners = sorted(world_vertices(a.body, a.pose), key=lambda v: v[2])[:4]
            errors = []
            for v in corners:
                errors.append(ground_error(backend.world, v) if V6 else _v5_ground_error(backend.world, v))
            error = q_up(max(errors)) if math.isfinite(max(errors)) else Fraction(1)
            limits = {'fixture_hash': self.fixture_hash, 'boot': backend.ownership.boot, 'world': str(backend.world.id),
                      'frame': frame_id, 'actor_id': a.id, 'body_pose_hash': _digest({'body': a.body, 'pose': a.pose}),
                      'maximum_ground_error_m': error, 'contact_method': 'recorded-ground-contact-v1',
                      'recipe_ref': recipe}
            raw = backend._raw(f'g4/ground-{a.role}.json', limits, frame_id, simtime)
            ground = self.proof('GROUND:' + a.role, 'recorded-ground-contact-v1', (raw,), UNC, limits, (recipe,),
                                ('native ground_projection witness; Claude review under Duy delegation, not independent',))
            out.append(replace(a, ground=ground))
        pair = self.fixture.pair
        context = {'pair_hash': pair.hash, 'reference': pair.reference, 'directed_route': self.fixture.routes['EGO'],
                   'uncertainty': {n: UNC for n in pair.names}}
        added = {'metric_context': context}
        predicate = self.fixture.environment.get('phase_predicate')
        if predicate is not None:  # signal-phase v1 S3: the same observe-only packet as in preparation
            self.phase = getattr(self, 'phase', None) or PhaseObserver(predicate['light'])
            added.update(self.phase.frame(backend, frame_id, simtime, ())[1])
        return tuple(out), added

    # -- seal ------------------------------------------------------------------------------------------------
    def initialization_recipe(self, store):
        a = append_record(store, 'g4/initialization-recipe.json', {
            'method': 'recorded-initialization-v1', 'version': '1',
            'limitations': 'spawn at frozen pose, initial speed 0; settle >= 1 s, readiness hold 0.50 s at frozen '
                           'targets/markers (prereg v2 section 4); first observation per errata E3/E5'})
        return ref_of(store.root / a.relativepath, 'G4_RECIPE')

    def _write(self, store, name, payload, kind='G4_SOURCE'):
        a = append_record(store, f'g4/{name}.json', payload)
        return ref_of(store.root / a.relativepath, kind)

    def finish(self, store, fixture, frames, boundary, pointers, context):
        from m56.evidence import _source_bytes
        extra = [self.authority, self.qualification, self.drivable_ref]
        added = {}
        why = 'Claude review under Duy delegation (A-G45), automated checks only, not independent'
        # W01
        w01 = json.loads(_source_bytes(pointers['w01_ref']))
        modules = tuple(context.identity.modules.values())
        added['w01_review_ref'] = self.review(w01, 'W01_OWNERSHIP', (pointers['w01_ref'], *modules),
                                              ('own server 2610, sole writer and tick owner; ' + why,))
        extra += [pointers['w01_ref'], *modules]
        # INITIALIZATION
        init = json.loads(_source_bytes(pointers['initialization_ref']))
        recipe = decode_ref(init['recipe_ref'])
        added['initialization_review_ref'] = self.review(init, 'INITIALIZATION', (pointers['initialization_ref'], recipe),
                                                         ('recorded runner clock/readiness; ' + why,))
        extra += [pointers['initialization_ref'], recipe]
        # COLLISION_DELIVERY
        backend = context.backend
        life = {'boot': boundary.boot, 'world': boundary.world,
                'channels': [dict(v) for v in backend.lifecycle.values()]}
        fence = {'boot': boundary.boot, 'world': boundary.world, 'recipe_hash': None,
                 'channels': [dict(v) for v in backend.fences.values()]}
        drecipe = {'schema': 1, 'method': 'recorded-ack-fence-v1', 'version': '1', 'limits': 'observed-owned-interval-only',
                   'qualification_refs': (self.qualification,)}
        dref = self._write(store, 'delivery-recipe', drecipe)
        fence['recipe_hash'] = dref.sha256
        lref, fref = self._write(store, 'delivery-lifecycle', life), self._write(store, 'delivery-fence', fence)
        trajectory_hash = _digest(tuple(frames))
        dreview = self.review(drecipe, 'COLLISION_DELIVERY_RECIPE', (dref, self.qualification), (why,))
        added['delivery_ref'] = self.proof('COLLISION_DELIVERY', 'recorded-ack-fence-v1', (lref, fref), Fraction(0),
                                           {'fixture_hash': self.fixture_hash, 'trajectory_hash': trajectory_hash,
                                            'recipe_ref': dref, 'recipe_review': dreview, 'lifecycle_ref': lref,
                                            'fence_ref': fref}, (dref,), (why,))
        extra += [dref, lref, fref]
        # CONTINUOUS_CONTACT + CONTINUOUS_MOTION. Recipe source_refs must be JSON sources (consumer _source_json):
        # a JSON receipt names the drivable-union WKT by hash (A/B 2026-10-24 found the bare .wkt ref rejected).
        dsrc = self._write(store, 'drivable-source', {'method': 'carla-generate-waypoints-0.5m-lane-quads-union',
                                                      'wkt': self.drivable_ref})
        extra.append(dsrc)
        contact_rows, motion_rows = [], []
        for a, b in zip(frames, frames[1:]):
            contact_rows.append(self._contact(a, b))
            motion_rows.append(self._motion(a, b))
        cr = self._write(store, 'contact-intervals', contact_rows)
        crecipe = {'method': 'bounded-contact-interval-v1', 'version': '1',
                   'quantities': ('body_separation', 'road_edge', 'ground_contact'), 'source_refs': (dsrc,)}
        crr = self._write(store, 'contact-recipe', crecipe)
        added['contact_ref'] = self.proof('CONTINUOUS_CONTACT', 'bounded-contact-interval-v1', (cr,), UNC,
                                          {'fixture_hash': self.fixture_hash, 'trajectory_hash': trajectory_hash,
                                           'recipe_ref': crr, 'recipe_review': self.review(crecipe, 'CONTACT_RECIPE',
                                                                                           (crr, dsrc, self.drivable_ref), (why,)),
                                           'intervals_ref': cr}, (crr,), (why,))
        mr = self._write(store, 'motion-intervals', motion_rows)
        mrecipe = {'method': 'bounded-motion-envelope-v1', 'version': '1',
                   'quantities': ('continuous_body_enclosure', 'reference_lateral_acceleration'),
                   'source_refs': (dsrc,)}
        mrr = self._write(store, 'motion-recipe', mrecipe)
        added['motion_ref'] = self.proof('CONTINUOUS_MOTION', 'bounded-motion-envelope-v1', (mr,), UNC,
                                         {'fixture_hash': self.fixture_hash, 'trajectory_hash': trajectory_hash,
                                          'recipe_ref': mrr, 'recipe_review': self.review(mrecipe, 'MOTION_RECIPE',
                                                                                          (mrr, dsrc, self.drivable_ref), (why,)),
                                          'intervals_ref': mr}, (mrr,), (why,))
        extra += [cr, crr, mr, mrr]
        return added, tuple(dict.fromkeys(extra))

    # -- interval bounds -------------------------------------------------------------------------------------
    @staticmethod
    def _footprint(actor):
        from shapely.geometry import MultiPoint
        return MultiPoint([(v[0], v[1]) for v in world_vertices(actor.body, actor.pose)]).convex_hull

    @staticmethod
    def _displacement(a, b):
        """Max vertex displacement of a rigid body between two observed poses (+1 mm for the rotation arc)."""
        va, vb = world_vertices(a.body, a.pose), world_vertices(b.body, b.pose)
        return max(math.dist(p, r) for p, r in zip(va, vb)) * 1.01 + 1e-3

    def _edge(self, actor):
        fp = self._footprint(actor)
        return fp.distance(self.boundary) if self.drivable.contains(fp) else -fp.distance(self.boundary)

    def _contact(self, a, b):
        roles = {x.role: x for x in a.actors}, {x.role: x for x in b.actors}
        d = {r: self._displacement(roles[0][r], roles[1][r]) for r in roles[0]}
        sep = [self._footprint(f['EGO']).distance(self._footprint(f['NPC'])) for f in roles]
        body = (sep[0] + sep[1] - d['EGO'] - d['NPC']) / 2  # each body point moves <= d along its path
        edge = min((self._edge(roles[0][r]) + self._edge(roles[1][r]) - d[r]) / 2 for r in roles[0])
        ground = max(x.ground.limits['maximum_ground_error_m'] for f in (a, b) for x in f.actors) + q_up(max(d.values()) * .02)
        return {'boot': a.boot, 'world': a.world, 'first_frame': a.frame, 'last_frame': b.frame,
                'first_actors_hash': _digest(a.actors), 'last_actors_hash': _digest(b.actors),
                'minimum_body_separation_m': q(body), 'minimum_road_edge_m': q(edge),
                'maximum_ground_error_m': ground, 'error_m': UNC}

    def _motion(self, a, b):
        from itertools import product
        actors = {}
        for x in a.actors:
            y = next(z for z in b.actors if z.role == x.role)
            pts = (*world_vertices(x.body, x.pose), *world_vertices(y.body, y.pose))
            pad = 1e-3 + self._displacement(x, y) * .01  # chord-to-arc slack of the small rotation
            # VertexSet is binary64 (consumer decoder); the 1 mm pad keeps the float rounding conservative
            low = tuple(float(q(min(p[k] for p in pts) - pad)) for k in range(3))
            high = tuple(float(q_up(max(p[k] for p in pts) + pad)) for k in range(3))
            box = tuple(tuple(high[k] if s[k] else low[k] for k in range(3)) for s in product((0, 1), repeat=3))
            response = next(r for r in self.fixture.responses if r.hash == y.commands[0].response_hash)
            target = (active_target(response, y.commands[0].cause) if V6 else max(v for v in response.targets.values()))
            actors[x.role] = {'actor_id': x.id, 'response_hash': y.commands[0].response_hash, 'envelope': box,
                              'reference_lateral_acceleration_bound_mps2': q_up(float(target) ** 2 * self.kappa(x.role, y))}
        return {'boot': a.boot, 'world': a.world, 'first_frame': a.frame, 'last_frame': b.frame,
                'first_actors_hash': _digest(a.actors), 'last_actors_hash': _digest(b.actors), 'actors': actors}

    def kappa(self, role, actor, window=10.):
        """Max |curvature| of the frozen reference route within +-window m of the actor's station."""
        route = self.fixture.routes[role]
        s = float(actor.arc) if actor.arc is not None else 0.
        t, arc = route.transforms, [float(x) for x in route.arc]
        k = 0.
        for i in range(1, len(t) - 1):
            if abs(arc[i] - s) <= window:
                dyaw = math.radians((t[i + 1].yaw - t[i - 1].yaw + 180) % 360 - 180)
                k = max(k, abs(dyaw) / (arc[i + 1] - arc[i - 1]))
        return k


def active_target(response, cause):
    """v6 d: the reference speed of the phase that issued this interval's command (NPC_TRAFFIC_HOLD = 0)."""
    return 0 if cause == 'NPC_TRAFFIC_HOLD' else response.targets[cause]


def decode_ref(packet):
    from m56.model import decode_record
    return decode_record('SourceRef', packet)


def _v5_ground_error(world, v):
    import carla
    g = world.ground_projection(carla.Location(v[0], v[1], v[2] + 2.), 10.)
    return abs(v[2] - g.location.z) if g is not None else math.inf


GROUND_RINGS = (.05, .1, .2, .3)  # m; prereg v6 c (seam probe 2026-10-26: NONE patches up to ~0.2 m around a corner)


def ground_error(world, v):
    """v6 c (prereg PREREG_M56_V6_20261026): the v5 corner ray; only when its hit is unlabelled (NONE, a ray through
    a hole of the road collision mesh, native ground/seam probes 2026-10-26) the search widens ring by ring (4 points
    at 0.05, 0.1, 0.2, 0.3 m) and stops at the first ring with a labelled hit: min error over that ring's labelled
    hits. No labelled hit at all = the v5 value. A labelled centre hit is exactly v5."""
    import carla
    g = world.ground_projection(carla.Location(v[0], v[1], v[2] + 2.), 10.)
    if g is not None and str(g.label) != 'NONE':
        return abs(v[2] - g.location.z)
    for d in GROUND_RINGS:
        errs = []
        for dx, dy in ((d, 0.), (-d, 0.), (0., d), (0., -d)):
            h = world.ground_projection(carla.Location(v[0] + dx, v[1] + dy, v[2] + 2.), 10.)
            if h is not None and str(h.label) != 'NONE':
                errs.append(abs(v[2] - h.location.z))
        if errs:
            return min(errs)
    return abs(v[2] - g.location.z) if g is not None else math.inf


class PhaseObserver:
    """Signal-phase v1 (prereg b4b6a22) S3: per tick, observe-only packet {light, state, tick_in_state} of the light
    whose OpenDRIVE id is `light`; tick_in_state = round(20 * get_elapsed_time()). Raw-retained. Never mutates."""

    def __init__(self, light_odr):
        self.light_odr, self.actor = str(light_odr), None

    @staticmethod
    def packet_of(light):
        """Signal-phase v1 erratum 3: L_N plus the whole group's [odr, state, elapsed ticks], sorted by odr."""
        # tuples: the decoded fixture environment carries tuples, and admission compares with ==
        group = tuple(sorted((str(t.get_opendrive_id()), str(t.get_state()), int(round(t.get_elapsed_time() * 20)))
                             for t in light.get_group_traffic_lights()))
        return {'light': str(light.get_opendrive_id()), 'group': group}

    def packet(self, backend):
        if self.actor is None:
            self.actor = next(t for t in backend.world.get_actors().filter('traffic.traffic_light')
                              if str(t.get_opendrive_id()) == self.light_odr)
        return self.packet_of(self.actor)

    def frame(self, backend, frame_id, simtime, actors):
        p = self.packet(backend)
        backend._raw('g4/phase.json', {**p, 'frame': frame_id, 'simtime': simtime}, frame_id, simtime)
        return actors, {'phase': p}
