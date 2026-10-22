"""Offline catalog identity, comparisons and gated admission. No native imports."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from fractions import Fraction
from itertools import combinations
from math import ceil
import hashlib
import json

from .model import (CandidateRevision, SiteLedger, CatalogAudit, ComparisonRecord,
                    ReviewRecord, SiteRecord, encode_record, ReleaseBlocked,
                    decode_record, decode_revision, load_json, SchemaErrors, FieldError,
                    IdentityMethod, Number, Candidate, PolicyBundle, SourceRef,
                    ReplacementLedger, ReplacementTransaction, ReplacementResult,
                    EpisodeVerdict, AdmissionVerdict, ActorRecipe, ParameterProposal)


_FIXTURE_DIGESTS = {}


def _digest(record: object) -> str:
    # A CompiledFixture is deeply frozen at construction (model._freeze), so its digest is memoized by identity
    # (strong ref kept) for per-tick online detection. ponytail: bounded clear-all cache.
    if type(record).__name__ == 'CompiledFixture':
        hit = _FIXTURE_DIGESTS.get(id(record))
        if hit is not None and hit[0] is record:
            return hit[1]
        if len(_FIXTURE_DIGESTS) > 256:
            _FIXTURE_DIGESTS.clear()
        _FIXTURE_DIGESTS[id(record)] = (record, _encode_digest(record))
        return _FIXTURE_DIGESTS[id(record)][1]
    return _encode_digest(record)


def _encode_digest(record: object) -> str:
    return hashlib.sha256(json.dumps(encode_record(record),sort_keys=True,
        separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def _site_digest(site: SiteRecord) -> str:
    return _digest({key:getattr(site,key) for key in
                   ('id','kind','geography','topology','interaction_refs')})


def _review_binds(review: ReviewRecord | None, digest: str, scopes: tuple[str,...]) -> bool:
    return (review is not None and review.object_hash==digest and review.scope in scopes
            and review.verdict=='APPROVED' and bool(review.refs) and bool(review.reasons)
            and bool(review.reviewer) and bool(review.date) and review.authority_ref is not None)


def check_catalog(candidates: CandidateRevision, sites: SiteLedger,
                  comparisons: tuple[ComparisonRecord,...]) -> CatalogAudit:
    towns=Counter(_town(c.town) for c in candidates.candidates)
    used=set(sites.assignments.get(c.id) for c in candidates.candidates)
    qualified=list({_domain_key(site):site for site in sites.records if site.id in used and
               _site_review_valid(site,sites.method,qualified=True)}.values())
    junctions=sum(site.kind=='JUNCTION' for site in qualified)
    deficits=list(_construction_deficits(candidates,sites))
    if junctions<23:
        deficits.append('JUNCTION_SHORTFALL')
    # This component does not possess the full AB/witness/release records.
    deficits.append('RELEASE_EVIDENCE_REQUIRED')
    return CatalogAudit({'proposed':len(candidates.candidates),'qualified_junctions':junctions,
                         'nonjunction_areas':sum(s.kind=='NONJUNCTION' for s in qualified),
                         'eligible':0,'distinct_towns':len(towns)}, dict(towns), {}, comparisons,
                         tuple(dict.fromkeys(deficits)),'RELEASE_BLOCKED')


def _town(town: str) -> str:
    return town.removesuffix('_Opt')


def _construction_deficits(revision: CandidateRevision, sites: SiteLedger) -> tuple[str,...]:
    candidates=revision.candidates
    deficits=[]
    target={cat:8 for cat in 'CILMO'}|{'F':6}
    if len(candidates)!=46 or Counter(c.category for c in candidates)!=target:
        deficits.append('CANDIDATE_COUNT')
    if len({c.id for c in candidates})!=len(candidates) or len({c.slot for c in candidates})!=len(candidates):
        deficits.append('DUPLICATE_CANDIDATE')
    towns={_town(c.town) for c in candidates}
    if not towns<={'Town04','Town05','Town06','Town07'}:
        deficits.append('TOWN_NOT_ALLOWED')
    if len(towns)<3:
        deficits.append('TOWN_SHORTFALL')
    if any(n>3 for n in Counter((c.category,_town(c.town)) for c in candidates).values()):
        deficits.append('CATEGORY_TOWN_CAP')
    if sites.freeze_ref is None:
        deficits.append('IDENTITY_METHOD_NOT_FROZEN')
    lookup={s.id:s for s in sites.records}
    if len(lookup)!=len(sites.records):
        deficits.append('DUPLICATE_SITE_ID')
    if set(sites.assignments)!={c.id for c in candidates}:
        deficits.append('SITE_ASSIGNMENT_COVERAGE')
    groups=[]
    for candidate in candidates:
        assigned=sites.assignments.get(candidate.id)
        site=lookup.get(assigned)
        if assigned!=candidate.site_id or site is None:
            deficits.append('SITE_ASSIGNMENT_INVALID')
            continue
        groups.append(_domain_key(site))
        if not _site_review_valid(site,sites.method):
            deficits.append('SITE_IDENTITY_UNRESOLVED')
        if candidate.category=='M' and not _category_proven(candidate,'M'):
            deficits.append('M_CATEGORY_UNPROVEN')
    if any(n>2 for n in Counter(groups).values()):
        deficits.append('SITE_CAP')
    return tuple(deficits)


def _domain_key(site: SiteRecord) -> str:
    # Same geography + topology + interaction evidence cannot be split by XML labels.
    return _digest((site.geography,site.topology,site.interaction_refs))


def _site_review_valid(site: SiteRecord, method: IdentityMethod, *, qualified=False) -> bool:
    return (site.kind in ('JUNCTION','NONJUNCTION') and bool(site.geography)
            and bool(site.topology) and bool(site.interaction_refs)
            and site.topology.get('method_hash')==method.hash
            and _review_binds(site.review,_site_digest(site),
                             ('SITE_QUALIFIED',) if qualified else ('SITE_IDENTITY','SITE_QUALIFIED')))


def _category_proven(candidate, category: str) -> bool:
    payload=candidate.environment.get('category_review')
    if payload is None:
        return False
    review=decode_record('ReviewRecord',encode_record(payload))
    digest=_digest((candidate.id,candidate.category,candidate.actors))
    return (isinstance(review,ReviewRecord) and
            _review_binds(review,digest,('CATEGORY:'+category,)) and
            (category!='M' or any(ref.method=='branch-to-mainflow-geometry-topology' for ref in review.refs)))


def freeze_c0(revision: CandidateRevision, sites: SiteLedger,
              review: ReviewRecord) -> CandidateRevision | ReleaseBlocked:
    reasons=list(_construction_deficits(revision,sites))
    if revision.c0_receipt is not None:
        reasons.append('C0_ALREADY_FROZEN')
    if not _review_binds(review,_digest({'revision':revision,'sites':sites}),('C0',)):
        reasons.append('C0_REVIEW_MISSING_OR_MISMATCHED')
    if any(not _complete_recipe(candidate) for candidate in revision.candidates):
        reasons.append('INCOMPLETE_CANDIDATE_RECIPE')
    if reasons:
        return ReleaseBlocked('C0_BLOCKED',tuple(dict.fromkeys(reasons)))
    return replace(revision,c0_receipt=review.authority_ref)


def _complete_recipe(candidate) -> bool:
    return (len(candidate.actors)==2 and {a.role for a in candidate.actors}=={'EGO','NPC'}
            and all(a.blueprint and a.initial_speed_mps==0 and (a.pose is not None or a.pose_recipe)
                    and a.route_recipe and a.destination is not None for a in candidate.actors)
            and len(candidate.responses)==2 and {r.action_id for r in candidate.responses}=={'A','B'}
            and all(r.actor_role=='EGO' and r.targets and r.phases for r in candidate.responses)
            and bool(candidate.parameters) and bool(candidate.refs)
            and bool(candidate.environment.get('weather')) and bool(candidate.environment.get('light')))


def load_candidates(path: Path) -> CandidateRevision | SchemaErrors:
    try:
        return decode_revision(load_json(path))
    except (OSError,ValueError) as exc:
        return SchemaErrors((FieldError(str(path),'INPUT_READ_FAILED:'+str(exc)),))


def review_sites(candidates: CandidateRevision, method: IdentityMethod,
                 evidence: tuple[ReviewRecord,...]) -> SiteLedger:
    """Import a source-hashed, reviewed identity packet; never infer sites from IDs.

    Packet schema: method_hash, records(SiteRecord[]), assignments(candidate->site).
    Missing/ambiguous reviews return unresolved (empty, unfrozen) ledger.
    """
    admitted=[]
    for review in evidence:
        if review.scope!='IDENTITY_LEDGER':
            continue
        for ref in review.refs:
            try:
                if not Path(ref.uri).is_absolute() or '://' in ref.uri:
                    continue
                raw=Path(ref.uri).read_bytes()
                if len(raw)!=ref.bytes or hashlib.sha256(raw).hexdigest()!=ref.sha256:
                    continue
                if not _review_binds(review,ref.sha256,('IDENTITY_LEDGER',)):
                    continue
                packet=load_json(Path(ref.uri))
                if (not isinstance(packet,dict) or set(packet)!={'method_hash','records','assignments'}
                        or packet['method_hash']!=method.hash):
                    continue
                ledger=decode_record('SiteLedger',{'method':encode_record(method),
                    'records':packet['records'],'assignments':packet['assignments'],
                    'freeze_ref':encode_record(ref)})
                if not isinstance(ledger,SiteLedger):
                    continue
                if set(ledger.assignments)!={c.id for c in candidates.candidates}:
                    continue
                if len({s.id for s in ledger.records})!=len(ledger.records):
                    continue
                if not all(_site_review_valid(site,method) for site in ledger.records):
                    continue
                admitted.append(ledger)
            except (OSError,ValueError,TypeError,KeyError):
                continue
    return admitted[0] if len(admitted)==1 else SiteLedger(method,(),{},None)


def delta(a: Number, b: Number) -> Number | None:
    if (isinstance(a,bool) or isinstance(b,bool) or not isinstance(a,(Fraction,int))
            or not isinstance(b,(Fraction,int)) or a<0 or b<0 or max(a,b)==0):
        return None
    return abs(Fraction(a)-Fraction(b))/max(abs(a),abs(b))


def compare_parameters(a: Candidate, b: Candidate, policies: PolicyBundle,
                       reviews: tuple[ReviewRecord,...]) -> ComparisonRecord:
    values=[]; deltas=[]; refs=[]; actions=[]; quantities=[]
    invalid=a.category!=b.category or a.id==b.id or not policies.receipt_refs
    keys={'unit','source_actions','aggregation','event','window','reference','physical_quantity','refs'}
    for name,descriptor in policies.descriptor_specs.items():
        if (set(descriptor)!=keys or not all(descriptor.get(k) for k in keys)
                or descriptor['aggregation']!='declared_scalar'
                or descriptor['unit'] not in ('m','m/s','s','m/s^2')):
            invalid=True
            continue
        left=a.parameters.get(name);right=b.parameters.get(name)
        if (left is None or right is None or len(left.values)!=1 or len(right.values)!=1
                or left.units!=right.units or left.units!=descriptor['unit']
                or not left.source or not right.source or not left.rationale or not right.rationale
                or left.status not in ('APPROVED_PROPOSAL_NOT_READY','APPROVED')
                or right.status not in ('APPROVED_PROPOSAL_NOT_READY','APPROVED')):
            invalid=True
            continue
        quantity=descriptor['physical_quantity']
        if quantity in quantities or quantity.lower() in {'id','coordinate','angle','label','index'}:
            invalid=True
            continue
        quantities.append(quantity)
        decoded=tuple(decode_record('SourceRef',encode_record(r)) for r in descriptor['refs'])
        if not decoded or not all(isinstance(r,SourceRef) for r in decoded):
            invalid=True
            continue
        refs.extend(decoded);actions.extend(descriptor['source_actions'])
        values.append((left.values[0],right.values[0]))
        deltas.append(delta(*values[-1]))
    binding=_digest({'a':a,'b':b,'policy':policies})
    review=next((r for r in reviews if _review_binds(r,binding,('DECLARED_COMPARABILITY_D09',))),None)
    status=('BLOCKED_COMPARABILITY' if invalid or len(values)<2 else
            'DIVERSITY_DEFICIT' if sum(d is not None and d>=Fraction(1,5) for d in deltas)<2 else
            'REVIEW_REQUIRED' if review is None else 'PASS')
    # No epsilon/automatic near-zero cutoff: every prospective pass needs bound D09 review.
    return ComparisonRecord((a.id,b.id),tuple(refs),tuple(dict.fromkeys(actions)),
                            'declared_scalar',tuple(values),tuple(deltas),status,review,'DECLARED')


def _exact_inputs(*values):
    if any(isinstance(v,bool) or not isinstance(v,(int,Fraction)) for v in values):
        raise ValueError('EXACT_SOURCE_NUMBER_REQUIRED')


def derive_g(vE: Number, vN: Number, LrefN: Number) -> Number:
    _exact_inputs(vE,vN,LrefN)
    vE,vN,LrefN=map(Fraction,(vE,vN,LrefN))
    if vE<=0 or vN<=0 or LrefN<=0:
        raise ValueError('POSITIVE_DESIGN_INPUT_REQUIRED')
    raw=vE*vE/3+vE/2+vE*(LrefN+5)/(2*vN)+Fraction(1,2)
    return Fraction(ceil(raw*2),2)


def derive_io_section(category: str, vE: Number, vN: Number, gap: Number,
                      t0s: Number, lane_id: int) -> Number:
    _exact_inputs(vE,vN,gap,t0s)
    vE,vN,gap,t0s=map(Fraction,(vE,vN,gap,t0s))
    if category not in ('I','O') or type(lane_id) is not int or lane_id==0:
        raise ValueError('INVALID_IO_DIRECTION')
    if vE<=0 or vN<=0 or gap<0 or t0s<0:
        raise ValueError('INVALID_IO_PHYSICAL_INPUT')
    dlc=3*vE
    if category=='I':
        distance=4*vE+dlc+Fraction(15,4)
    else:
        if vN!=Fraction(5,2) or vE<=vN:
            raise ValueError('O_RECIPE_REQUIRES_2_5_LEAD_AND_FASTER_EGO')
        return_start=max(dlc,vE*(gap+Fraction(9,2)+Fraction(9,2)+Fraction(1,2))/(vE-vN))
        distance=return_start+dlc+Fraction(15,4)
    station=t0s+(-distance if lane_id>0 else distance)
    if station<0:
        raise ValueError('BLOCKED_FIXTURE_SECTION_OUTSIDE_ROAD')
    return station


def audit_diversity(revision: CandidateRevision, policies: PolicyBundle,
                    reviews: tuple[ReviewRecord,...]) -> tuple[ComparisonRecord,...]:
    if len({c.id for c in revision.candidates})!=len(revision.candidates):
        raise ValueError('DUPLICATE_CANDIDATE')
    return tuple(compare_parameters(a,b,policies,reviews)
                 for category in ('C','I','L','M','O','F')
                 for a,b in combinations((c for c in revision.candidates if c.category==category),2))


def _successor_binding(ledger: ReplacementLedger, transaction: ReplacementTransaction) -> str:
    return _digest({'c0_hash':ledger.c0_hash,'history':ledger.transactions,'used':ledger.used,
                    'transaction':replace(transaction,approval=None)})


def admit_successor(ledger: ReplacementLedger, transaction: ReplacementTransaction,
                    approval: ReviewRecord) -> ReplacementResult:
    if not ledger.c0_hash:
        return ReplacementResult('BLOCKED_C0',ledger,('C0_REQUIRED',))
    if ledger.used!=len(ledger.transactions) or ledger.used<0:
        return ReplacementResult('INVALID_LEDGER',ledger,('COUNTER_MISMATCH',))
    history=ReplacementLedger(ledger.c0_hash,(),0)
    seen=set(); latest={}
    for previous in ledger.transactions:
        if (previous.id in seen or previous.counters!=(history.used,history.used+1)
                or previous.old_hash==previous.new_hash
                or (previous.slot in latest and latest[previous.slot]!=previous.old_hash)
                or not _review_binds(previous.approval,_successor_binding(history,previous),
                                     ('SUCCESSOR_ADMISSION',))):
            return ReplacementResult('INVALID_LEDGER',ledger,('HISTORY_MISMATCH',))
        seen.add(previous.id); latest[previous.slot]=previous.new_hash
        history=replace(history,used=history.used+1,transactions=history.transactions+(previous,))
    if ledger.used>=9:
        return ReplacementResult('REPLACEMENT_LIMIT',ledger,('EXACT_NINE_LIMIT',))
    if (transaction.id in {t.id for t in ledger.transactions}
            or transaction.counters!=(ledger.used,ledger.used+1)
            or transaction.old_hash==transaction.new_hash
            or transaction.phase not in ('PRE_DELIVERY','POST_DELIVERY')
            or not transaction.refs or not transaction.reason):
        return ReplacementResult('REPLACEMENT_BLOCKED',ledger,('INVALID_TRANSACTION',))
    previous=next((t for t in reversed(ledger.transactions) if t.slot==transaction.slot),None)
    if previous is not None and previous.new_hash!=transaction.old_hash:
        return ReplacementResult('REPLACEMENT_BLOCKED',ledger,('PREDECESSOR_MISMATCH',))
    if not _review_binds(approval,_successor_binding(ledger,transaction),('SUCCESSOR_ADMISSION',)):
        return ReplacementResult('REPLACEMENT_BLOCKED',ledger,('REVIEW_MISMATCH',))
    admitted=replace(transaction,approval=approval)
    return ReplacementResult('ADMITTED',replace(ledger,used=ledger.used+1,
                                  transactions=ledger.transactions+(admitted,)),())


def classify_failure(verdict: EpisodeVerdict, review: ReviewRecord) -> str:
    if (verdict.physical!='FAILED' and
            _review_binds(review,_digest(verdict),('UNCHANGED_SCENE_HARNESS_FIX',))):
        return 'TECHNICAL_FIX_NO_RERUN'
    if verdict.physical=='FAILED':
        return 'SCENE_FAILURE_REVIEW_REQUIRED'
    if verdict.witness!='VALID' or verdict.physical in ('UNKNOWN','INCOMPLETE','NOT_RUN'):
        return 'INFRASTRUCTURE_UNCERTAINTY_NO_AUTOREPLACEMENT'
    return 'REVIEW_REQUIRED'


def validation_precondition(revision: CandidateRevision) -> AdmissionVerdict:
    """Catalog-only prerequisite, never grants runtime authority; runtime also admits G4/G5."""
    if revision.c0_receipt is None or len(revision.candidates)!=46:
        return AdmissionVerdict('BLOCKED_C0',('COMPLETE_FROZEN_C0_REQUIRED',))
    return AdmissionVerdict('C0_PRESENT_NOT_RUNTIME_AUTHORITY',('G4_G5_STILL_REQUIRED',),
                            (revision.c0_receipt,))


# --- T15 global eligibility, whitelisted rendering and exclusive export ---

_ENV_FIELDS = ('weather', 'light')
_ENV_PROVENANCE = ('category_review',)  # provenance only: carried in refs, never rendered as scene content
_FORBIDDEN = ('npc_driver', 'npc_program', 'npc_controller', 'driver', 'controller', 'agent', 'behavior', 'gains',
              'program')


def _forbidden(key) -> bool:
    k = str(key).lower()
    return any(f == k or k.startswith(f + '_') or k.endswith('_' + f) for f in _FORBIDDEN)


def render_catalog(candidates: CandidateRevision) -> list[dict[str, object]] | SchemaErrors:
    """Whitelist only. Unknown fields are rejected (never stripped); NPC driver/program/gains are forbidden."""
    errors, out = [], []
    for c in candidates.candidates:
        here = f'candidates[{c.id}]'
        for key in (*c.parameters, *c.environment):
            if _forbidden(key):
                errors.append(FieldError(f'{here}.{key}', 'NPC_PROGRAM_ASSIGNMENT_FORBIDDEN'))
        for key in c.environment:
            if key not in (*_ENV_FIELDS, *_ENV_PROVENANCE) and not _forbidden(key):
                errors.append(FieldError(f'{here}.environment.{key}', 'FIELD_NOT_WHITELISTED'))
        if any(not c.environment.get(k) for k in _ENV_FIELDS):
            errors.append(FieldError(f'{here}.environment', 'WEATHER_OR_LIGHT_MISSING'))
        actors = []
        for a in c.actors:
            if a.pose is None or a.destination is None or not a.route_recipe:
                errors.append(FieldError(f'{here}.actors[{a.role}]', 'POSE_ROUTE_OR_DESTINATION_NOT_MATERIALIZED'))
                continue
            for key in (*a.pose_recipe, *a.route_recipe):
                if _forbidden(key):
                    errors.append(FieldError(f'{here}.actors[{a.role}].{key}', 'NPC_PROGRAM_ASSIGNMENT_FORBIDDEN'))
            actors.append({'role': a.role, 'blueprint': a.blueprint, 'initial_speed_mps': a.initial_speed_mps,
                           'pose': {k: getattr(a.pose, k) for k in ('x', 'y', 'z', 'pitch', 'yaw', 'roll')},
                           'route': a.route_recipe, 'destination': a.destination})
        out.append({'id': c.id, 'slot': c.slot, 'version': c.version, 'category': c.category, 'town': c.town,
                    'site_id': c.site_id, 'actors': actors, 'parameters': dict(c.parameters),
                    'ego_alternatives': [{'action_id': r.action_id, 'targets': r.targets, 'profile': r.profile,
                                          'phases': r.phases} for r in c.responses if r.actor_role == 'EGO'],
                    'environment': {k: c.environment[k] for k in _ENV_FIELDS if k in c.environment},
                    'provenance': {'lineage': c.lineage, 'refs': c.refs}})
    return SchemaErrors(tuple(errors)) if errors else [encode_record(e) for e in out]


def _refs(value):
    from collections.abc import Mapping
    from dataclasses import fields as dc_fields, is_dataclass
    if isinstance(value, SourceRef):
        yield value
    elif isinstance(value, Mapping):
        for v in value.values():
            yield from _refs(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from _refs(v)
    elif is_dataclass(value):
        for f in dc_fields(value):
            yield from _refs(getattr(value, f.name))


def _source_verified(ref: SourceRef) -> bool:
    try:
        path = Path(ref.uri)
        data = path.read_bytes() if '://' not in ref.uri and path.is_absolute() else None
    except OSError:
        return False
    return data is not None and len(data) == ref.bytes and hashlib.sha256(data).hexdigest() == ref.sha256


def _release_deficits(candidates: CandidateRevision, audit: CatalogAudit, evidence) -> list[str]:
    deficits = list(audit.deficits)
    if candidates.c0_receipt is None:
        deficits.append('C0_MISSING')
    if len(candidates.candidates) != 46:
        deficits.append('CANDIDATE_COUNT')
    if audit.counts.get('qualified_junctions', 0) < 23:
        deficits.append('JUNCTION_SHORTFALL')
    keys = [frozenset(r.pair_ids) for r in audit.comparisons]
    if (len(keys) != 155 or len(set(keys)) != 155
            or any(r.status != 'PASS' or r.review is None or not r.descriptor_refs
                   or r.declared_or_realized != 'REALIZED' for r in audit.comparisons)):
        deficits.append('COMPARISON_COVERAGE')
    ids = {c.id for c in candidates.candidates}
    passed = {e.scene for e in evidence if e.scene in ids and e.AB.status == 'PASS' and e.review
              and len(e.AB.action_proofs) == 2 and e.AB.review is not None
              and all((p.spawn, p.physical, p.witness) == ('CONFIRMED', 'COMPLETE', 'VALID') for p in e.AB.action_proofs)}
    if passed != ids or len(evidence) != len(ids):
        deficits.append('AB_PROOF')
    refs = list(_refs((evidence, audit.comparisons, candidates.c0_receipt)))
    if any(r.kind.upper().startswith('SYNTHETIC') or '://' in r.uri for r in refs):
        deficits.append('SYNTHETIC_EVIDENCE')
    elif not refs or any(not _source_verified(r) for r in refs):
        deficits.append('EVIDENCE_SOURCE_UNVERIFIED')
    return list(dict.fromkeys(deficits))


def summarize(candidates: CandidateRevision, audit: CatalogAudit, evidence) -> dict[str, object]:
    deficits = _release_deficits(candidates, audit, evidence)
    return {'counts': {'proposed': len(candidates.candidates),
                       'eligible': sum(e.AB.status == 'PASS' for e in evidence),
                       'qualified_junctions': audit.counts.get('qualified_junctions', 0),
                       'comparisons': len(audit.comparisons)},
            'deficits': deficits, 'status': 'RELEASE_BLOCKED' if deficits else 'RELEASE_READY'}


def export_catalog(candidates: CandidateRevision, audit: CatalogAudit, evidence, target: Path):
    """One JSON list, created exclusively, only when every global release deficit is absent."""
    from .model import ArtifactRef, ExportReceipt
    target = Path(target)
    deficits = _release_deficits(candidates, audit, evidence)
    rendered = render_catalog(candidates)
    if isinstance(rendered, SchemaErrors):
        deficits.append('RENDER_SCHEMA_ERROR')
    if target.exists():
        deficits.append('TARGET_EXISTS')
    if deficits:
        return ReleaseBlocked('RELEASE_BLOCKED', tuple(dict.fromkeys(deficits)))
    data = (json.dumps(rendered, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=1) + '\n').encode('utf-8')
    try:
        with target.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        return ReleaseBlocked('RELEASE_BLOCKED', ('TARGET_EXISTS',))
    return ExportReceipt('EXPORTED', ArtifactRef(target.name, hashlib.sha256(data).hexdigest(), len(data), 'CATALOG'),
                         tuple(dict.fromkeys(_refs(evidence))))


# --- T17 source-bound import of the retained 26 and authorized staging (no selection, no tuning) ---

_TARGETS = {'C': 8, 'I': 8, 'L': 8, 'M': 8, 'O': 8, 'F': 6}
_SPEED_E = {'C': Fraction(4), 'L': Fraction(2), 'M': Fraction(4)}  # ref06 §3/§4/§5 proposed Ego speeds
_PENDING = {'status': 'PENDING_RUNTIME_QUERY'}


def _src(path: Path, kind: str = 'APPROVED_SOURCE') -> SourceRef:
    data = Path(path).read_bytes()
    return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'sha256', kind)


def _exact(text: str) -> Fraction:
    text = text.strip()
    return Fraction(text.split('=')[0].split('≈')[0]) if '/' in text else Fraction(text)


def import_retained(spec: Path, ref06: Path) -> CandidateRevision | SchemaErrors:
    """Parse the approved spec §6.3 (C/L/M) and §7.4 (I/O) rows plus ref06 site/alias/connection rows.

    Routes must agree between both documents; poses/destinations/weather stay PENDING_RUNTIME_QUERY.
    """
    import re
    spec_ref, ref06_ref = _src(spec), _src(ref06)
    spec_lines = Path(spec).read_text(encoding='utf-8').splitlines()
    ref_lines = Path(ref06).read_text(encoding='utf-8').splitlines()
    errors, out = [], []
    rows06 = {}
    for line in ref_lines:
        m = re.match(r'\|\s*M56-P-([CILMO]\d\d)(?:/(A0\d-R\d+))?\s*\|', line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        routes = re.findall(r'`([^`]*→[^`]*)`\s*\((c\d+)\)', line)
        site = m.group(2) or (re.match(r'0\d/(P0\d-J\w+)', cells[1]).group(1) if re.match(r'0\d/(P0\d-J\w+)', cells[1]) else None)
        aliases = re.findall(r'`([^`→]+)`', cells[2]) if m.group(1)[0] == 'L' else []
        rows06[m.group(1)] = {'site': site, 'routes': routes, 'aliases': aliases, 'cells': cells}

    def actor(role, route, connection):
        return ActorRecipe(role, 'vehicle.audi.a2', Fraction(0), None, dict(_PENDING),
                           {'route': route, 'connection': connection, 'notation': 'road/lane→connector/lane→outgoing/lane'},
                           None)

    def proposal(name, value, units, rationale, status='APPROVED_PROPOSAL_NOT_READY'):
        return ParameterProposal(name, (value,), units, rationale, (spec_ref,), status)

    for line in spec_lines:
        m = re.match(r'\|([CLM]0\d)\|0(\d)/(J\w+)\|([^|]+)\|([^|]+)\|(\d)\|([\d.]+)\|([\d.]+)\s*\|', line)
        if m:
            slot, town, junction, e_route, n_route, k, lref, g = m.groups()
            r06 = rows06.get(slot)
            if r06 is None or r06['site'] != f'P0{town}-{junction}':
                errors.append(FieldError(slot, 'REF06_SITE_MISMATCH')); continue
            if [r for r, _ in r06['routes']] != [e_route.strip(), n_route.strip()]:
                errors.append(FieldError(slot, 'SOURCE_ROUTE_MISMATCH')); continue
            (_, ce), (_, cn) = r06['routes']
            k = int(k)
            params = {'vE': proposal('vE', _SPEED_E[slot[0]], 'm/s', 'ref06 proposed Ego speed', 'RETAINED_PROPOSAL'),
                      'vN': proposal('vN', Fraction(3) * Fraction(5, 4) ** (k - 1), 'm/s', 'spec §6.3 exact k-expression'),
                      'LrefN': proposal('LrefN', Fraction(lref), 'm', 'spec §6.3 pinned connector road/@length'),
                      'G': proposal('G', Fraction(g), 'm', 'spec §6.2 G0 grid 0.50 m')}
            env = {'weather': dict(_PENDING, policy='STOCK_DEFAULT_RECORD_ALL_FIELDS'),
                   'light': dict(_PENDING, policy='STOCK_DEFAULT_RECORD_ALL_FIELDS'),
                   'aliases': {'stable_id': f'M56-P-{slot}', 'short_id': slot, 'k_index': k,
                               **({'original_left_id': r06['aliases'][0], 'ego_direction_id': r06['aliases'][1]}
                                  if slot[0] == 'L' and len(r06['aliases']) >= 2 else {})}}
            out.append(Candidate(f'M56-P-{slot}', slot, 'ref06-20261006+spec-8e1e2ba3', (), slot[0], f'Town0{town}',
                                 r06['site'], (actor('EGO', e_route.strip(), ce), actor('NPC', n_route.strip(), cn)),
                                 params, (), env, (spec_ref, ref06_ref)))
            continue
        m = re.match(r'\|([IO]0\d)\|0(\d)/(R\d+) ([^|]+)\|([^/|]+)/([^;|]+);([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|', line)
        if m:
            slot, town, road, lanes, ve, vn, gap, front, dlc, ret, x = m.groups()
            r06 = rows06.get(slot)
            if r06 is None or r06['site'] != f'A0{town}-{road}':
                errors.append(FieldError(slot, 'REF06_SITE_MISMATCH')); continue
            params = {'vE': proposal('vE', _exact(ve), 'm/s', 'spec §7.4'),
                      'vN': proposal('vN', _exact(vn), 'm/s', 'spec §7.4'),
                      'gap': proposal('gap', _exact(gap), 'm', 'spec §7.4 bumper gap at trigger'),
                      'front_t0': proposal('front_t0', _exact(front), 'm', 'spec §7.4 front t0 road-s'),
                      'Dlc': proposal('Dlc', _exact(dlc), 'm', 'spec §7.4 Dlc=3*vE'),
                      'X': proposal('X', _exact(x), 'm', 'spec §7.4 rear-end X road-s')}
            if ret.strip() != '—':
                params['return_start'] = proposal('return_start', _exact(ret), 'm', 'spec §7.4 O return start')
            env = {'weather': dict(_PENDING, policy='STOCK_DEFAULT_RECORD_ALL_FIELDS'),
                   'light': dict(_PENDING, policy='STOCK_DEFAULT_RECORD_ALL_FIELDS'),
                   'aliases': {'stable_id': f'M56-P-{slot}', 'short_id': slot, 'lanes': lanes.strip(),
                               'ref06_roles': r06['cells'][1]}}
            roles = r06['cells'][1]
            out.append(Candidate(f'M56-P-{slot}', slot, 'ref06-20261006+spec-8e1e2ba3', (), slot[0], f'Town0{town}',
                                 r06['site'], (actor('EGO', roles, None), actor('NPC', roles, None)), params, (), env,
                                 (spec_ref, ref06_ref)))
    if len(out) != 26 and not errors:
        errors.append(FieldError('import', f'RETAINED_COUNT:{len(out)}'))
    if errors:
        return SchemaErrors(tuple(errors))
    return CandidateRevision('retained-26-ref06-spec8e1e2ba3', tuple(out),
                             _digest((spec_ref.sha256, ref06_ref.sha256)), None)


def stage_inputs(base: CandidateRevision, additions: tuple[Candidate, ...], policies: PolicyBundle,
                 source_refs: tuple[SourceRef, ...]):
    """Stage retained + authorized additions; never selects sites, invents G or promotes proposals."""
    from .model import CampaignInputs
    errors = []
    verified = {(r.sha256, r.bytes) for r in source_refs if _source_verified(r)}
    if len(verified) != len({(r.sha256, r.bytes) for r in source_refs}):
        errors.append(FieldError('sources', 'SOURCE_REF_UNVERIFIED'))
    for c in base.candidates:
        if not c.refs or any((r.sha256, r.bytes) not in verified for r in c.refs):
            errors.append(FieldError(f'base[{c.id}]', 'BASE_SOURCE_UNBOUND'))
    if base.c0_receipt is not None:
        errors.append(FieldError('base', 'C0_ALREADY_FROZEN'))
    ids = {c.id for c in base.candidates}
    for c in additions:
        here = f'additions[{c.id}]'
        if c.id in ids:
            errors.append(FieldError(here, 'DUPLICATE_CANDIDATE'))
        ids.add(c.id)
        receipts = [r for r in c.refs if r.kind == 'M56_SELECTION_RECEIPT' and (r.sha256, r.bytes) in verified]
        review = decode_record('ReviewRecord', encode_record(c.environment.get('selection_review'))) \
            if c.environment.get('selection_review') is not None else None
        bare = replace(c, environment={k: v for k, v in c.environment.items() if k != 'selection_review'})
        if not receipts or not isinstance(review, ReviewRecord) or not _review_binds(review, _digest(bare), ('M56_SELECTION',)):
            errors.append(FieldError(here, 'SELECTION_AUTHORITY_MISSING'))
            continue
        rationale = c.environment.get('rationale_review')
        rationale = decode_record('ReviewRecord', encode_record(rationale)) if rationale is not None else None
        if not isinstance(rationale, ReviewRecord) or not _review_binds(rationale, _digest(c.parameters),
                                                                         ('PARAMETER_RATIONALE',)):
            errors.append(FieldError(here, 'RATIONALE_REVIEW_MISSING'))
    for name, p in policies.approved_parameters.items():
        if name.startswith('F0') and p.status not in ('APPROVED_PROPOSAL_NOT_READY', 'UNRESOLVED'):
            errors.append(FieldError(f'policies.{name}', 'F_PROPOSAL_PROMOTION_FORBIDDEN'))
    if errors:
        return SchemaErrors(tuple(errors))
    candidates = (*base.candidates, *additions)
    counts = Counter(c.category for c in candidates)
    revision = CandidateRevision(f'{base.revision_id}+{len(additions)}', tuple(candidates),
                                 _digest(tuple((r.sha256, r.bytes) for r in source_refs)), None)
    deficits = {'missing_slots': {k: n - counts.get(k, 0) for k, n in _TARGETS.items() if n - counts.get(k, 0) > 0},
                'counts': dict(counts), 'c0': 'NOT_FROZEN', 'g3': 'NOT_GRANTED'}
    return CampaignInputs(revision, policies, tuple(source_refs), deficits)
