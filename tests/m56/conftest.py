"""Synthetic-only helpers; no CARLA/stock imports or native permission."""
import copy
import importlib
import importlib.abc
import sys
from types import SimpleNamespace

import pytest


class NativeImportDenied(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'carla', 'agents'}:
            raise AssertionError(f'UNAUTHORIZED_NATIVE_IMPORT: {fullname}')
        return None


@pytest.fixture(autouse=True)
def no_native_import():
    guard = NativeImportDenied()
    assert 'carla' not in sys.modules
    sys.meta_path.insert(0, guard)
    yield
    sys.meta_path.remove(guard)
    assert 'carla' not in sys.modules


@pytest.fixture
def require():
    def lookup(module, symbol):
        try:
            loaded = importlib.import_module(module)
        except ModuleNotFoundError as exc:
            if exc.name not in {module, module.split('.')[0]}:
                raise
            pytest.fail(f'Missing planned production module: {module}', pytrace=False)
        if not hasattr(loaded, symbol):
            pytest.fail(f'Missing planned production behavior: {module}.{symbol}', pytrace=False)
        return getattr(loaded, symbol)
    return lookup


def raw_revision():
    pose = dict(x=0, y=0, z=0, pitch=0, yaw=0, roll=0)
    actors = [dict(role=role, blueprint='vehicle.audi.a2', initial_speed_mps='0',
                   pose=pose.copy(), pose_recipe={'kind': 'SYNTHETIC_TEST'},
                   route_recipe={'kind': 'SYNTHETIC_TEST'}, destination=None)
              for role in ('EGO', 'NPC')]
    candidate = dict(id='SYNTHETIC_C01', slot='C01', version='test', lineage=(),
                     category='C', town='Town04', site_id='SYNTHETIC_SITE', actors=actors,
                     parameters={}, responses=(), environment={'kind': 'SYNTHETIC_TEST'}, refs=())
    return dict(revision_id='SYNTHETIC_TEST', candidates=[candidate], source_hash='a'*64,
                c0_receipt=None)


@pytest.fixture
def case():
    def make_case(name, **changes):
        payload = copy.deepcopy(raw_revision())
        if name == 'nonfinite-pose':
            payload['candidates'][0]['actors'][0]['pose']['x'] = changes['x']
        else:
            raise AssertionError(f'Unknown synthetic fixture: {name}')
        return SimpleNamespace(payload=payload)
    return make_case


@pytest.fixture
def catalog_case():
    """Hand-authored artificial sites; never stock-map selection/approval evidence."""
    def make(count=46, junctions=23):
        from dataclasses import replace
        from fractions import Fraction
        from m56.model import (SourceRef, ReviewRecord, CandidateRevision, Candidate,
            ActorRecipe, Transform6, FrozenResponse, IdentityMethod, SiteRecord, SiteLedger)
        import hashlib
        import json
        from m56.model import encode_record
        ref=SourceRef('synthetic://test', 'a'*64, 1,'test','literal','SYNTHETIC_TEST')
        review=lambda obj,scope: ReviewRecord(obj,scope,(ref,), 'SYNTHETIC_TEST',
                      '2026-10-08','APPROVED',('hand-authored software fixture',),ref)
        categories=[cat for cat in 'CILMO' for _ in range(8)]+['F']*6
        candidates=[]
        records=[]
        assignments={}
        for i,cat in enumerate(categories[:count]):
            slot=f'{cat}{categories[:i+1].count(cat):02}'
            site=f'SYNTHETIC_SITE_{i//2:02}'
            role_actors=tuple(ActorRecipe(role,'vehicle.audi.a2',Fraction(0),
                Transform6(0,0,0,0,0,0),{'kind':'SYNTHETIC_TEST'},
                {'kind':'SYNTHETIC_TEST'},Fraction(10)) for role in ('EGO','NPC'))
            responses=tuple(FrozenResponse('EGO',action,None,{},
                         {'kind':'SYNTHETIC_TEST'}, {}, 'b'*64) for action in ('A','B'))
            category_proof=review('b'*64, 'CATEGORY:'+cat)
            candidate=Candidate(slot,slot,'test',(),cat,f'Town{4+(categories[:i].count(cat)%3):02}',
                   site,role_actors,{},responses,{'kind':'SYNTHETIC_TEST',
                   'category_review':encode_record(category_proof)},(ref,))
            candidates.append(candidate)
            assignments[slot]=site
        for i in range((count+1)//2):
            site=f'SYNTHETIC_SITE_{i:02}'
            kind='JUNCTION' if i<junctions else 'NONJUNCTION'
            geography={'domain_key':f'SYNTHETIC_DOMAIN_{i:02}'}
            topology={'method_hash':'b'*64,'category':'SYNTHETIC_TEST'}
            payload={'id':site,'kind':kind,'geography':geography,'topology':topology,
                     'interaction_refs':(ref,)}
            digest=hashlib.sha256(json.dumps(encode_record(payload),sort_keys=True,
                     separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
            records.append(SiteRecord(site,kind,geography,topology,(ref,),review(digest,'SITE_QUALIFIED')))
        revision=CandidateRevision('SYNTHETIC_TEST',tuple(candidates),'c'*64,None)
        method=IdentityMethod('synthetic-identity','1','b'*64,
                              {'basis':('geography','topology','interaction')})
        ledger=SiteLedger(method,tuple(records),assignments,ref)
        return SimpleNamespace(revision=revision,sites=ledger,comparisons=(),ref=ref,
                               review=review('c'*64,'C0'),review_factory=review)
    return make


@pytest.fixture
def replacement_case(catalog_case):
    def make(used=9):
        from dataclasses import replace
        import hashlib,json
        from m56.model import ReplacementTransaction,ReplacementLedger,encode_record
        c=catalog_case()
        ledger=ReplacementLedger('c'*64,(),0)
        def proposal(ledger,phase='PRE_DELIVERY'):
            old=ledger.transactions[-1].new_hash if ledger.transactions else 'd'*64
            return ReplacementTransaction(f'tx-{ledger.used+1}','C01',old,
                     f'{ledger.used+1:064x}',phase,'SCENE_SUCCESSOR',(c.ref,),
                     'SYNTHETIC_TEST',None,(ledger.used,ledger.used+1))
        def review_for(ledger,tx):
            value={'c0_hash':ledger.c0_hash,'history':ledger.transactions,
                   'used':ledger.used,'transaction':replace(tx,approval=None)}
            h=hashlib.sha256(json.dumps(encode_record(value),sort_keys=True,
                    separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
            return c.review_factory(h,'SUCCESSOR_ADMISSION')
        for i in range(used):
            tx=proposal(ledger,'POST_DELIVERY' if i%2 else 'PRE_DELIVERY')
            tx=replace(tx,approval=review_for(ledger,tx))
            ledger=ReplacementLedger(ledger.c0_hash,ledger.transactions+(tx,),i+1)
        tx=proposal(ledger,'POST_DELIVERY')
        return SimpleNamespace(ledger=ledger,transaction=tx,review=review_for(ledger,tx),
                               review_for=review_for,proposal=proposal,ref=c.ref)
    return make


@pytest.fixture
def parameter_case(catalog_case):
    def make():
        from dataclasses import replace
        from fractions import Fraction
        from m56.model import ParameterProposal, PolicyBundle, encode_record
        c=catalog_case()
        candidates=[]
        for candidate,speed,gap in zip(c.revision.candidates[:2],('3','3.75'),('26','22.5')):
            params={name:ParameterProposal(name,(Fraction(value),),unit,'hand-derived',
                        (c.ref,),'APPROVED_PROPOSAL_NOT_READY')
                    for name,value,unit in (('vN',speed,'m/s'),('G',gap,'m'))}
            candidates.append(replace(candidate,parameters=params))
        descriptors={name:{'unit':unit,'source_actions':('A','B'),'aggregation':'declared_scalar',
                          'event':'READY','window':('READY','TRIGGER'),
                          'reference':'frozen_source','physical_quantity':name,
                          'refs':(encode_record(c.ref),)} for name,unit in (('vN','m/s'),('G','m'))}
        policy=PolicyBundle('test','b'*64,{}, {},descriptors,(c.ref,))
        return SimpleNamespace(a=candidates[0],b=candidates[1],policies=policy,ref=c.ref)
    return make
