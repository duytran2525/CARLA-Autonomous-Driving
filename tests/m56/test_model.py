"""Catches acceptance of nonfinite pose coordinates at the actual decoder."""


def test_rejects_nonfinite_pose(require, case):
    decode = require('m56.model', 'decode_revision')
    out = decode(case('nonfinite-pose', x=float('nan')).payload)
    assert out.status == 'SCHEMA_ERROR'
    assert out.errors[0].path == 'candidates[0].actors[0].pose.x'


def test_units_not_silently_converted(require):
    # Wrong-unit speed must never become an admitted initial state.
    parameter = require('m56.model', 'decode_record')('ParameterProposal', {
        'name':'speed', 'values':['4'], 'units':'mph', 'rationale':'test',
        'source':[], 'status':'APPROVED_PROPOSAL_NOT_READY',
    })
    assert parameter.status == 'SCHEMA_ERROR'
    assert parameter.errors[0].path == 'units'


def test_naked_authority_boolean_rejected(require):
    decode = require('m56.model', 'decode_record')
    out = decode('ApprovalBundle', {'approved': True})
    assert out.status == 'SCHEMA_ERROR'
    assert out.errors[0].reason == 'UNKNOWN_FIELD'


def test_source_value_roundtrip(require):
    from fractions import Fraction
    number = require('m56.model', 'number')
    encode = require('m56.model', 'encode_record')
    decode = require('m56.model', 'decode_record')
    out = decode('ParameterProposal', {
        'name':'speed', 'values':[encode(number('0.8000000001'))], 'units':'m/s',
        'rationale':'SYNTHETIC_TEST', 'source':[], 'status':'APPROVED_PROPOSAL_NOT_READY',
    })
    assert out.values == (Fraction(8000000001,10000000000),)


def test_offline_model_import_has_no_carla(require):
    require('m56.model', 'decode_revision')
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    program = (
        'import sys,socket;'
        f'sys.path.insert(0,{str(root)!r});'
        'socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError("NETWORK"));'
        'import m56.model;'
        'assert "carla" not in sys.modules;assert "agents" not in sys.modules;'
        'print("NO_NATIVE_MODULE_OR_NETWORK")'
    )
    process = subprocess.run([sys.executable,'-I','-B','-X','utf8','-c',program],
                             capture_output=True,text=True,timeout=10)
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == 'NO_NATIVE_MODULE_OR_NETWORK'


def test_unknown_key_rejected_in_every_record_schema(require):
    decode = require('m56.model', 'decode_record')
    import m56.model as model
    for name in model._RECORDS:
        out = decode(name, {'unrecognized':0})
        assert out.status == 'SCHEMA_ERROR', name
        assert out.errors[0].reason == 'UNKNOWN_FIELD', name


def test_declared_json_decimal_does_not_become_binary64(require,tmp_path):
    from fractions import Fraction
    load = require('m56.model', 'load_json')
    decode = require('m56.model', 'decode_record')
    path=tmp_path/'parameter.json'
    path.write_text('{"name":"gap","values":[25.35],"units":"m",'
                    '"rationale":"SYNTHETIC_TEST","source":[],"status":"PROPOSAL"}')
    out=decode('ParameterProposal',load(path))
    assert out.values == (Fraction(507,20),)


def test_measured_binary64_roundtrip_preserves_hex(require):
    encode=require('m56.model','encode_record')
    decode=require('m56.model','decode_record')
    from m56.model import Transform6
    pose=Transform6(0.1,-0.0,1,0,0,0)
    encoded=encode(pose)
    assert encoded['x'] == {'binary64':'0x1.999999999999ap-4'}
    result=decode('Transform6',encoded)
    assert result.x.hex() == '0x1.999999999999ap-4'
    assert result.y.hex() == '-0x0.0p+0'


def test_decode_freezes_nested_mappings(require):
    import pytest
    decode = require('m56.model','decode_record')
    out=decode('ApprovalBundle',{'receipt_refs':[], 'object_hashes':{'C0':'a'*64},
                                 'allowed_scopes':['offline']})
    with pytest.raises(TypeError):
        out.object_hashes['C0']='b'*64


def test_unknown_verdict_axis_rejected(require):
    decode = require('m56.model', 'decode_record')
    out = decode('EpisodeVerdict', dict(spawn='CONFIRMED', physical='MAYBE_PASS',
                 witness='VALID', reasons=[], events=[], metrics={}))
    assert out.status == 'SCHEMA_ERROR'
    assert out.errors[0].path == 'physical'


def test_frozen_direct_constructor_copies_nested_data(require):
    import pytest
    cls=require('m56.model','ApprovalBundle')
    source={'C0':'a'*64}
    out=cls((),source,('offline',))
    source['C0']='b'*64
    assert out.object_hashes['C0']=='a'*64
    with pytest.raises(TypeError):
        out.object_hashes['C0']='c'*64


def test_numeric_provenance_tags_roundtrip_inside_packet_fields(require):
    from fractions import Fraction as F
    encode=require('m56.model','encode_record')
    decode=require('m56.model','decode_record')
    from m56.model import CapabilityProof
    packet=CapabilityProof('BODY_FIT','synthetic',(),F(1,1000),
                           {'minimum_road_edge_m':F(1,5),'observed':0.1},None,'UNKNOWN')
    out=decode('CapabilityProof',encode(packet))
    assert out.limits==packet.limits
    assert out.limits['observed'].hex()==0.1.hex()


def test_declared_float_fields_have_stable_canonical_roundtrip(require):
    from fractions import Fraction as F
    from m56.model import Section
    encode=require('m56.model','encode_record')
    decode=require('m56.model','decode_record')
    value=Section(((0,1,2),(0,3,4),(0,5,6)),(1,0,0),F(3),{'z_min':F(0)})
    assert encode(decode('Section',encode(value)))==encode(value)
