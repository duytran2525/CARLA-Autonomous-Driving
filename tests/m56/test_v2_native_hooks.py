"""M56 runtime-recipe v2 product changes (errata E1/E3/E5, 2026-10-23): first-observation rule with the old rule kept
for reporting, and runner-owned collision instrumentation. Synthetic, no native import."""
from fractions import Fraction as F
from types import SimpleNamespace

from m56.model import (ActorFrame, AdmissionVerdict, BodyRecord, OwnershipReceipt, RuntimeIdentity, SourceRef,
                       SpawnResponse, Transform6)

REF = SourceRef('synthetic://v2', 'a' * 64, 1, 'test', 'literal', 'SYNTHETIC_TEST')
BODY = BodyRecord((0., 0., .78), (0., 0., 0.), (1.85, .89, .77), (), 'vehicle.audi.a2', {}, {}, REF)
FROZEN = Transform6(264.6748690540891, -310.83084383956896, .014348602145910263, 0., -179.41021596910656, 0.)


def actor(pose, velocity=(0., 0., 0.)):
    return ActorFrame('EGO', 1, pose, velocity, BODY, F(0), {}, (), None, None, 1, True, None)


def test_settling_first_observation_matches_new_rule_only():
    from m56.evidence import _initial_state_matches
    # native g4 probe 2026-10-23: float32 x/y/yaw, z down 1.8 mm, pitch 0.007 deg; engineering vz -0.029 m/s
    observed = Transform6(264.6748046875, -310.8308410644531, .012529373168945312, .006959962192922831,
                          -179.4102020263672, 0.)
    assert _initial_state_matches(actor(observed, (-.0006, 0., -.029)), FROZEN)
    assert observed != FROZEN  # the old exact rule fails for every native spawn


def test_new_rule_rejects_real_initial_motion_or_misplacement():
    from dataclasses import replace
    from m56.evidence import _initial_state_matches
    good = Transform6(264.6748046875, -310.8308410644531, .0125, 0., -179.4102020263672, 0.)
    assert not _initial_state_matches(actor(good, (.2, 0., 0.)), FROZEN)          # moving > 0.10 m/s
    assert not _initial_state_matches(actor(replace(good, x=264.70)), FROZEN)    # 2.5 cm off in x
    assert not _initial_state_matches(actor(replace(good, z=.05)), FROZEN)       # above the frozen pose
    assert not _initial_state_matches(actor(replace(good, z=-.01)), FROZEN)      # dropped > 2 cm
    assert not _initial_state_matches(actor(replace(good, pitch=.5)), FROZEN)    # tilted
    assert not _initial_state_matches(actor(replace(good, yaw=-179.0)), FROZEN)  # turned


def test_instrumented_spawn_registers_runner_sensors_not_scene_actors(tmp_path):
    from m56.evidence import open_run
    from m56.model import ActorRecipe
    from m56.runtime import spawn_owned
    calls = []
    backend = SimpleNamespace(
        identity=lambda: SimpleNamespace(boot='b1', world='w7'),
        spawn=lambda actors, cue: tuple(SpawnResponse(101 + i, None, REF) for i, _ in enumerate(actors)),
        instrument=lambda vehicles: (calls.append(dict(vehicles)), (201, 202))[1],
        listen=lambda sensor_id, callback: calls.append(('listen', sensor_id)))
    ctx = SimpleNamespace(backend=backend, identity=RuntimeIdentity('b1', 'w7', '0.9.16', '0.9.16', '3.12.10', {}, 'h', {}),
                          ownership=OwnershipReceipt('b1', 'w7', '127.0.0.1', 1, 's', {'rpc': 2610}, (F(0), F(9)), 'm', 'm', ()),
                          admission=AdmissionVerdict('ADMITTED', ()), store=open_run(tmp_path / 'run', 'r1', 'm'))
    fixture = SimpleNamespace(actors=tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), FROZEN, {}, {}, None) for r in ('EGO', 'NPC')))
    registry = spawn_owned(ctx, fixture)
    assert registry.owned_vehicle_ids == (101, 102)
    assert registry.owned_sensor_ids == (201, 202)
    assert len(registry.spawn_responses) == 2  # scene actors only: roles map stays {EGO, NPC}
    assert calls[0] == {'EGO': 101, 'NPC': 102}
    assert ('listen', 201) in calls and ('listen', 202) in calls
