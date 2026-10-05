"""CARLA runner for fixed counterfactual NPC-response fixtures."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    import carla  # type: ignore
except ImportError:  # pragma: no cover
    carla = None

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .controllers import ReactiveYieldController, RouteSpeedController, speed_from_schedule
from .scenario_catalog import ACTOR_STATE_FIELDS, PROFILES, ActorSpec, SceneSpec, TransformSpec, config_hash


LOG = logging.getLogger(__name__)


class ExperimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExperimentConfig:
    host: str = "127.0.0.1"
    port: int = 2000
    tm_port: int = 8000
    timeout_s: float = 60.0
    town: str = "Town03"
    fixed_delta_s: float = 0.05
    no_rendering: bool = True
    base_seed: int = 41021
    repetitions: int = 10
    run_duration_s: float = 14.0
    warmup_ticks: int = 2
    expected_server_version_prefix: str = "0.9.16"
    output_dir: str = "outputs/ego_intent_response"
    catalog_path: str = "configs/ego_intent_response_town03_scenes.yaml"
    initial_position_tolerance_m: float = 0.10
    initial_speed_tolerance_mps: float = 0.25
    initial_yaw_tolerance_deg: float = 0.5
    max_setup_attempts: int = 2
    tm_following_distance_m: float = 4.0
    reactive_min_ttc_s: float = 3.0
    reactive_occupancy_radius_m: float = 6.0
    reactive_follow_gap_m: float = 10.0
    reload_world_each_run: bool = True

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ExperimentConfig":
        section = raw.get("experiment", raw)
        if not isinstance(section, Mapping):
            raise ExperimentError("Experiment configuration must be a mapping.")
        aliases = {"timeout": "timeout_s", "fixed_delta": "fixed_delta_s"}
        values = {aliases.get(str(key), str(key)): value for key, value in section.items()}
        valid = {field.name for field in cls.__dataclass_fields__.values()}
        unexpected = set(values) - valid
        if unexpected:
            raise ExperimentError(f"Unknown experiment config keys: {sorted(unexpected)}")
        config = cls(**values)
        positive = (config.fixed_delta_s, config.timeout_s, config.initial_position_tolerance_m,
                    config.initial_speed_tolerance_mps, config.initial_yaw_tolerance_deg,
                    config.tm_following_distance_m, config.reactive_min_ttc_s,
                    config.reactive_occupancy_radius_m, config.reactive_follow_gap_m)
        if any(not math.isfinite(v) or v <= 0 for v in positive) or config.repetitions < 1 or not math.isfinite(config.run_duration_s) or config.run_duration_s < 13.05 or config.max_setup_attempts < 1:
            raise ExperimentError("Invalid experiment timing, count or tolerance; duration must cover the analysis window (>=13.05 s).")
        return config


def load_experiment_config(path: str | Path) -> tuple[ExperimentConfig, dict[str, Any]]:
    if yaml is None:
        raise ExperimentError("PyYAML is required for the experiment configuration.")
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, Mapping):
        raise ExperimentError("Experiment config root must be a mapping.")
    return ExperimentConfig.from_mapping(raw), dict(raw)


def seed_for(base_seed: int, scene_index: int, repeat: int) -> int:
    return int(base_seed) + int(scene_index) * 1000 + int(repeat)


def simulation_config(config: ExperimentConfig) -> dict[str, Any]:
    """Fields affecting observations; transport/output paths do not alter them."""
    ignored = {"host", "port", "tm_port", "timeout_s", "output_dir", "catalog_path", "repetitions", "max_setup_attempts"}
    return {key: value for key, value in asdict(config).items() if key not in ignored}


def implementation_hash() -> str:
    """Prevent resume from mixing observations after controller/setup changes."""
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for name in ("runner.py", "controllers.py", "scenario_catalog.py"):
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return digest.hexdigest()


def _route_length(route: Sequence[TransformSpec]) -> float:
    return sum(math.hypot(right.x - left.x, right.y - left.y) for left, right in zip(route, route[1:]))


def _transform(spec: TransformSpec) -> Any:
    assert carla is not None
    return carla.Transform(carla.Location(x=spec.x, y=spec.y, z=spec.z), carla.Rotation(yaw=spec.yaw_deg))


def _initial_velocity(spec: TransformSpec, speed: float) -> Any:
    assert carla is not None
    yaw = math.radians(spec.yaw_deg)
    return carla.Vector3D(x=float(speed) * math.cos(yaw), y=float(speed) * math.sin(yaw), z=0.0)


def _actor_checksum(actor_specs: Iterable[ActorSpec]) -> str:
    payload = [
        {"actor_key": spec.actor_key, "type": spec.blueprint, "transform": spec.transform.as_dict(), "speed": spec.initial_speed_mps}
        for spec in actor_specs
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class CarlaExperimentWorld:
    """Owns only experiment actors and never deletes actors it did not create."""

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.client: Any = None
        self.world: Any = None
        self.tm: Any = None
        self._original_settings: Any = None
        self._owned_actors: list[Any] = []
        self._owned_sensors: list[Any] = []
        self._collision_actors: set[int] = set()
        self._collision_events: list[dict[str, Any]] = []
        self._original_weather: Any = None
        self._original_lights: list[tuple[Any, Any, bool]] = []
        self._provenance: dict[str, Any] | None = None

    def start(self) -> None:
        if carla is None:
            raise ExperimentError("CARLA Python API is unavailable.")
        self.client = carla.Client(self.config.host, int(self.config.port))
        self.client.set_timeout(float(self.config.timeout_s))
        server_version = str(self.client.get_server_version())
        client_version = str(self.client.get_client_version())
        if not server_version.startswith(self.config.expected_server_version_prefix):
            raise ExperimentError(
                f"Expected CARLA server {self.config.expected_server_version_prefix}*, got {server_version}."
            )
        if server_version.split("-")[0] != client_version.split("-")[0]:
            raise ExperimentError(f"CARLA client/server mismatch: client={client_version}, server={server_version}.")
        self.world = self.client.get_world()
        self._require_empty_world()
        current_map = self.world.get_map().name.replace("\\", "/").split("/")[-1]
        if current_map.lower() != self.config.town.lower():
            settings = self.world.get_settings()
            settings.no_rendering_mode = bool(self.config.no_rendering)
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = self.config.fixed_delta_s
            self.world.apply_settings(settings)
            self.world = self.client.load_world(self.config.town, False)
        self.tm = self.client.get_trafficmanager(int(self.config.tm_port))
        self._original_settings = self.world.get_settings()
        self._original_weather = self.world.get_weather()
        self._original_lights = [(light, light.get_state(), light.is_frozen()) for light in self.world.get_actors().filter("traffic.traffic_light*")]
        self._apply_settings()
        self._set_fixed_environment()
        self._provenance = self.provenance()

    def _apply_settings(self) -> None:
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = float(self.config.fixed_delta_s)
        settings.no_rendering_mode = bool(self.config.no_rendering)
        settings.substepping = True
        settings.max_substep_delta_time = 0.01
        settings.max_substeps = max(10, math.ceil(self.config.fixed_delta_s / 0.01))
        self.world.apply_settings(settings)
        self.tm.set_synchronous_mode(True)

    def _require_empty_world(self) -> None:
        assert self.world is not None
        actors = self.world.get_actors()
        foreign = list(actors.filter("vehicle.*")) + list(actors.filter("walker.pedestrian.*"))
        if foreign:
            identities = [f"{getattr(actor, 'id', '?')}:{getattr(actor, 'type_id', '?')}" for actor in foreign[:8]]
            raise ExperimentError(
                "Experiment server must have no ambient vehicle/walker actors; found " + ", ".join(identities)
            )

    def _set_fixed_environment(self, light_state: str = "Green") -> None:
        assert self.world is not None and carla is not None
        self.world.set_weather(carla.WeatherParameters.ClearNoon)
        for light in self.world.get_actors().filter("traffic.traffic_light*"):
            light.set_state(getattr(carla.TrafficLightState, light_state))
            light.freeze(True)

    def provenance(self) -> dict[str, Any]:
        if self._provenance is not None:
            return dict(self._provenance)
        assert self.world is not None and self.client is not None
        carla_map = self.world.get_map()
        opendrive = carla_map.to_opendrive()
        return {
            "server_version": str(self.client.get_server_version()),
            "client_version": str(self.client.get_client_version()),
            "map_name": str(carla_map.name),
            "opendrive_sha256": hashlib.sha256(opendrive.encode("utf-8")).hexdigest(),
            "fixed_delta_s": self.config.fixed_delta_s,
            "no_rendering": self.config.no_rendering,
        }

    def _spawn_actor(self, spec: ActorSpec) -> Any:
        assert self.world is not None
        blueprint = self.world.get_blueprint_library().find(spec.blueprint)
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute("role_name", f"experiment_{spec.actor_key}")
        actor = self.world.try_spawn_actor(blueprint, _transform(spec.transform))
        if actor is None:
            raise ExperimentError(f"Cannot spawn {spec.actor_key} ({spec.blueprint}) at fixed transform.")
        self._owned_actors.append(actor)
        actor.apply_control(carla.VehicleControl())
        return actor

    def spawn_fixture(self, scene: SceneSpec) -> dict[str, Any]:
        self.cleanup_fixture()
        self._require_empty_world()
        if self.config.reload_world_each_run:
            self.world = self.client.reload_world(False)
            self.tm = self.client.get_trafficmanager(self.config.tm_port)
            self._apply_settings()
        self._set_fixed_environment(scene.traffic_light_state)
        actors = {scene.ego.actor_key: self._spawn_actor(scene.ego)}
        for spec in scene.npcs:
            actors[spec.actor_key] = self._spawn_actor(spec)
        for _ in range(max(20, int(self.config.warmup_ticks))):
            self.world.tick()
        # Spin up wheels before injecting the measured initial velocity. A
        # velocity command on stationary wheels produces alternating tire-slip
        # impulses (especially at low speeds). Keep every actor at its pinned
        # pose during this unrecorded calibration, so no interaction is consumed.
        warmup_controllers = {spec.actor_key: RouteSpeedController(spec.route, dt=self.config.fixed_delta_s)
                              for spec in [scene.ego, *scene.npcs]}
        for _ in range(100):
            for spec in [scene.ego, *scene.npcs]:
                actor = actors[spec.actor_key]
                pose = _transform(spec.transform)
                pose.location.z = actor.get_location().z
                actor.set_transform(pose)
                output = warmup_controllers[spec.actor_key].step(actor, spec.initial_speed_mps)
                actor.apply_control(carla.VehicleControl(throttle=output.throttle, brake=output.brake))
            self.world.tick()
        # Preserve the settled ground height and compensate the one initial
        # physics step. Commands become observable in the next world snapshot.
        compensation = {spec.actor_key: 0.0 for spec in [scene.ego, *scene.npcs]}
        for calibration_step in range(24):
            for spec in [scene.ego, *scene.npcs]:
                actor = actors[spec.actor_key]
                transform = _transform(spec.transform)
                velocity = _initial_velocity(spec.transform, spec.initial_speed_mps + compensation[spec.actor_key])
                transform.location.z = actor.get_location().z
                transform.location.x -= velocity.x * self.config.fixed_delta_s
                transform.location.y -= velocity.y * self.config.fixed_delta_s
                actor.set_transform(transform)
                actor.set_target_velocity(velocity)
                actor.set_target_angular_velocity(carla.Vector3D())
                actor.apply_control(carla.VehicleControl())
            self.world.tick()
            valid, validation_errors = self.validate_initial_state(scene, actors)
            LOG.debug("Initial calibration %d: compensation=%s, errors=%s", calibration_step, compensation, validation_errors)
            if valid:
                break
            for spec in [scene.ego, *scene.npcs]:
                v = actors[spec.actor_key].get_velocity()
                # Relax the feedback: tire slip creates an oscillatory response
                # if the complete speed error is added in a single step.
                compensation[spec.actor_key] += 0.25 * (spec.initial_speed_mps - math.hypot(v.x, v.y))
        return actors

    def attach_collision_sensors(self, actors: Mapping[str, Any]) -> None:
        assert self.world is not None and carla is not None
        blueprint = self.world.get_blueprint_library().find("sensor.other.collision")
        for actor in actors.values():
            sensor = self.world.spawn_actor(blueprint, carla.Transform(), attach_to=actor)
            actor_id = int(actor.id)
            sensor.listen(lambda event, actor_id=actor_id: self._on_collision(event, actor_id))
            self._owned_sensors.append(sensor)

    def reset_seed(self, seed: int) -> None:
        assert self.tm is not None
        self.tm.set_random_device_seed(int(seed))

    def _on_collision(self, event: Any, actor_id: int) -> None:
        self._collision_actors.add(actor_id)
        self._collision_events.append(dict(frame=int(event.frame), actor_id=actor_id, other_actor_id=int(event.other_actor.id)))

    def configure_tm_actor(self, actor: Any, spec: ActorSpec) -> None:
        assert self.tm is not None
        actor.set_autopilot(True, int(self.config.tm_port))
        self.tm.auto_lane_change(actor, False)
        self.tm.distance_to_leading_vehicle(actor, float(self.config.tm_following_distance_m))
        self.tm.ignore_lights_percentage(actor, 0.0)
        self.tm.ignore_signs_percentage(actor, 0.0)
        self.tm.ignore_vehicles_percentage(actor, 0.0)
        locations = [carla.Location(x=point.x, y=point.y, z=point.z) for point in spec.route]
        try:
            self.tm.set_path(actor, locations)
        except Exception as exc:
            raise ExperimentError("Traffic Manager set_path is required for pinned NPC routes.") from exc
        self.tm.set_desired_speed(actor, float(spec.tm_speed_mps) * 3.6)

    def validate_initial_state(self, scene: SceneSpec, actors: Mapping[str, Any]) -> tuple[bool, list[str]]:
        messages: list[str] = []
        expected = [scene.ego, *scene.npcs]
        for spec in expected:
            actor = actors[spec.actor_key]
            location = actor.get_location()
            position_error = math.hypot(location.x - spec.transform.x, location.y - spec.transform.y)
            velocity = actor.get_velocity()
            expected_v = _initial_velocity(spec.transform, spec.initial_speed_mps)
            speed_error = math.hypot(velocity.x-expected_v.x, velocity.y-expected_v.y)
            yaw_error = abs((actor.get_transform().rotation.yaw - spec.transform.yaw_deg + 180) % 360 - 180)
            if position_error > self.config.initial_position_tolerance_m:
                messages.append(f"{spec.actor_key}: position_error={position_error:.3f}m")
            if speed_error > self.config.initial_speed_tolerance_mps:
                messages.append(f"{spec.actor_key}: velocity_error={speed_error:.3f}m/s")
            if yaw_error > self.config.initial_yaw_tolerance_deg:
                messages.append(f"{spec.actor_key}: yaw_error={yaw_error:.3f}deg")
        return not messages, messages

    def collided(self, actor: Any) -> bool:
        return int(actor.id) in self._collision_actors

    def cleanup_fixture(self) -> None:
        had_owned_actors = bool(self._owned_actors or self._owned_sensors)
        for sensor in self._owned_sensors:
            try:
                sensor.stop()
            except Exception:
                pass
            try:
                sensor.destroy()
            except Exception:
                pass
        self._owned_sensors = []
        for actor in self._owned_actors:
            try:
                actor.destroy()
            except Exception:
                pass
        self._owned_actors = []
        self._collision_actors.clear()
        self._collision_events.clear()
        if had_owned_actors and self.world is not None:
            # CARLA's client actor cache refreshes on the next snapshot. Flush
            # deletion commands before checking for foreign traffic/reloading.
            self.world.tick()

    def close(self) -> None:
        self.cleanup_fixture()
        if self.tm is not None:
            try:
                self.tm.set_synchronous_mode(False)
            except Exception:
                pass
        if self.world is not None and self._original_settings is not None:
            try:
                self.world.set_weather(self._original_weather)
                lights = self.world.get_actors().filter("traffic.traffic_light*")
                for light, (_old, state, frozen) in zip(lights, self._original_lights):
                    light.set_state(state)
                    light.freeze(frozen)
                self.world.apply_settings(self._original_settings)
            except Exception:
                pass


def preflight_scene(world: Any, scene: SceneSpec) -> list[str]:
    """Validate pinned fixture topology without spawning actors."""
    errors: list[str] = []
    road_map = world.get_map()
    for spec in [scene.ego, *scene.npcs]:
        waypoint = road_map.get_waypoint(_transform(spec.transform).location, project_to_road=False)
        if waypoint is None or not bool(getattr(waypoint, "lane_type", 0) & carla.LaneType.Driving):
            errors.append(f"{spec.actor_key}: fixed start is not on a driving lane")
        if _route_length(spec.route) < 40.0:
            errors.append(f"{spec.actor_key}: fixed route is shorter than 40m")
        for i, p in enumerate(spec.route):
            wp = road_map.get_waypoint(_transform(p).location, project_to_road=False, lane_type=carla.LaneType.Driving)
            if wp is None:
                errors.append(f"{spec.actor_key}: route point {i} outside driving lane")
    for intent_id, intent in scene.intents.items():
        if _route_length(intent.route) < 40:
            errors.append(f"{intent_id}: route shorter than 40m")
        for i, p in enumerate(intent.route):
            if road_map.get_waypoint(_transform(p).location, project_to_road=False, lane_type=carla.LaneType.Driving) is None:
                errors.append(f"{intent_id}: route point {i} outside driving lane")
    actors = [scene.ego, *scene.npcs]
    for index, left in enumerate(actors):
        for right in actors[index + 1:]:
            gap = math.hypot(left.transform.x - right.transform.x, left.transform.y - right.transform.y)
            if gap < 5.0:
                errors.append(f"{left.actor_key}/{right.actor_key}: initial overlap gap={gap:.2f}m")
    ego_ttc = math.hypot(scene.ego.transform.x - scene.conflict_zone.x, scene.ego.transform.y - scene.conflict_zone.y) / max(scene.ego.initial_speed_mps, 0.25)
    critical = [npc for npc in scene.npcs if npc.critical]
    if not critical:
        errors.append("No critical NPC")
    for npc in critical:
        npc_ttc = math.hypot(npc.transform.x - scene.conflict_zone.x, npc.transform.y - scene.conflict_zone.y) / max(npc.initial_speed_mps, 0.25)
        if abs(ego_ttc - npc_ttc) > 8.0:
            errors.append(f"{npc.actor_key}: expected TTC mismatch={abs(ego_ttc - npc_ttc):.2f}s")
        nearest_zone = min(math.hypot(p.x-scene.conflict_zone.x, p.y-scene.conflict_zone.y) for p in npc.route)
        if nearest_zone > scene.conflict_zone.radius_m:
            errors.append(f"{npc.actor_key}: route misses conflict zone")
        angle = abs((scene.ego.transform.yaw_deg - npc.transform.yaw_deg + 180) % 360 - 180)
        if scene.category == "unprotected_left" and angle < 150:
            errors.append(f"{npc.actor_key}: left-turn fixture is not opposed by oncoming traffic")
        if scene.category == "cross_traffic" and not 65 < angle < 115:
            errors.append(f"{npc.actor_key}: crossing fixture lacks perpendicular approaches")
        if scene.category not in {"unprotected_left", "cross_traffic"} and angle > 20:
            errors.append(f"{npc.actor_key}: longitudinal/lane-change fixture has incompatible driving directions")
    active_route = next(iter(scene.intents.values())).route
    if min(math.hypot(p.x-scene.conflict_zone.x, p.y-scene.conflict_zone.y) for p in active_route) > scene.conflict_zone.radius_m:
        errors.append("Ego maneuver route misses conflict zone")
    return errors


def _row_for_actor(
    *, run_id: str, scene: SceneSpec, profile: str, intent: str, repeat: int, seed: int,
    tick: int, time_s: float, actor_key: str, actor_role: str, actor: Any, simulation_time_s: float | None = None,
    control: Any, collision: bool, reaction_reason: str, controller_mode: str,
) -> dict[str, Any]:
    transform = actor.get_transform()
    location = transform.location
    velocity = actor.get_velocity()
    acceleration = actor.get_acceleration()
    return {
        "run_id": run_id, "scene_id": scene.scene_id, "category": scene.category, "profile": profile,
        "intent": intent, "repeat": repeat, "seed": seed, "tick": tick, "time_s": simulation_time_s if simulation_time_s is not None else time_s,
        "relative_time_s": time_s, "actor_key": actor_key, "actor_id": int(actor.id), "actor_role": actor_role,
        "actor_type": str(actor.type_id), "x": location.x, "y": location.y, "z": location.z,
        "yaw_deg": transform.rotation.yaw, "vx": velocity.x, "vy": velocity.y, "vz": velocity.z,
        "speed_mps": math.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2),
        "ax": acceleration.x, "ay": acceleration.y, "az": acceleration.z,
        "throttle": float(getattr(control, "throttle", 0.0)), "brake": float(getattr(control, "brake", 0.0)),
        "steer": float(getattr(control, "steer", 0.0)), "hand_brake": bool(getattr(control, "hand_brake", False)),
        "collision": bool(collision), "reaction_reason": reaction_reason, "controller_mode": controller_mode,
    }


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig, config_payload: Mapping[str, Any], catalog_hash: str = "") -> None:
        self.config = config
        self.config_payload = dict(config_payload)
        self.environment = CarlaExperimentWorld(config)
        self.output_dir = Path(config.output_dir).resolve()
        self.catalog_hash = catalog_hash
        self.code_hash = implementation_hash()
        self.effective_hash = config_hash({"simulation": simulation_config(config), "implementation_hash": self.code_hash})

    def start(self) -> None:
        self.environment.start()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "experiment_config.json").write_text(
            json.dumps({"config": asdict(self.config), "config_hash": self.effective_hash, "catalog_hash": self.catalog_hash, "implementation_hash": self.code_hash}, indent=2) + "\n",
            encoding="utf-8",
        )

    def close(self) -> None:
        self.environment.close()

    def preflight(self, scenes: Iterable[SceneSpec]) -> dict[str, list[str]]:
        assert self.environment.world is not None
        result = {scene.scene_id: preflight_scene(self.environment.world, scene) for scene in scenes}
        path = self.output_dir / "preflight.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result

    def _run_paths(self, scene: SceneSpec, profile: str, intent: str, repeat: int, *, output_group: str = "runs") -> tuple[Path, Path]:
        root = self.output_dir / output_group / profile / scene.scene_id / intent / f"rep_{repeat:02d}"
        return root / "states.csv", root / "metadata.json"

    def is_complete(self, scene: SceneSpec, profile: str, intent: str, repeat: int, *, output_group: str = "runs") -> bool:
        states_path, metadata_path = self._run_paths(scene, profile, intent, repeat, output_group=output_group)
        if not states_path.exists() or not metadata_path.exists():
            return False
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("status") != "complete" or metadata.get("config_hash") != self.effective_hash or metadata.get("catalog_hash") != self.catalog_hash:
                return False
            digest = hashlib.sha256(states_path.read_bytes()).hexdigest()
            return digest == metadata.get("states_sha256")
        except Exception:
            return False

    def check_existing_cell(self, scene: SceneSpec, profile: str, intent: str, repeat: int, *, output_group: str = "runs") -> None:
        """Never overwrite complete observations from a different experiment."""
        _, metadata_path = self._run_paths(scene, profile, intent, repeat, output_group=output_group)
        if not metadata_path.exists():
            return
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise ExperimentError(f"Unreadable existing metadata: {metadata_path}") from exc
        if metadata.get("status") == "complete" and (metadata.get("config_hash") != self.effective_hash or metadata.get("catalog_hash") != self.catalog_hash):
            raise ExperimentError(f"Existing cell belongs to a different configuration/catalog/implementation: {metadata_path}; choose a new output directory")

    def run_single(
        self,
        scene: SceneSpec,
        *,
        profile: str,
        intent_id: str,
        repeat: int,
        scene_index: int,
        seed_override: int | None = None,
        output_group: str = "runs",
    ) -> dict[str, Any]:
        if profile not in PROFILES:
            raise ExperimentError(f"Unsupported NPC profile: {profile}")
        if intent_id not in scene.intents:
            raise ExperimentError(f"{scene.scene_id} has no intent {intent_id}.")
        intent = scene.intents[intent_id]
        seed = int(seed_override) if seed_override is not None else seed_for(self.config.base_seed, scene_index, repeat)
        run_id = f"{scene.scene_id}_{profile}_{intent_id}_{output_group}_r{repeat:02d}"
        states_path, metadata_path = self._run_paths(scene, profile, intent_id, repeat, output_group=output_group)
        self.check_existing_cell(scene, profile, intent_id, repeat, output_group=output_group)
        states_path.parent.mkdir(parents=True, exist_ok=True)
        actors: dict[str, Any] = {}
        status = "invalid"
        error = ""
        setup_messages: list[str] = []
        try:
            actors = self.environment.spawn_fixture(scene)
            self.environment.reset_seed(seed)
            valid, setup_messages = self.environment.validate_initial_state(scene, actors)
            if not valid:
                raise ExperimentError("Initial-state validation failed: " + "; ".join(setup_messages))
            self.environment.attach_collision_sensors(actors)
            initial_states = {key: dict(x=a.get_location().x, y=a.get_location().y, z=a.get_location().z, yaw_deg=a.get_transform().rotation.yaw,
                                       vx=a.get_velocity().x, vy=a.get_velocity().y, vz=a.get_velocity().z) for key, a in actors.items()}
            initial_snapshot = self.environment.world.get_snapshot()
            prefix_controller = RouteSpeedController(scene.ego.route, dt=self.config.fixed_delta_s)
            ego_controller = RouteSpeedController(intent.route, dt=self.config.fixed_delta_s)
            reactive_controllers: dict[str, ReactiveYieldController] = {}
            for npc in scene.npcs:
                if profile == "tm_default" or not npc.critical:
                    self.environment.configure_tm_actor(actors[npc.actor_key], npc)
                else:
                    reactive_controllers[npc.actor_key] = ReactiveYieldController(
                        RouteSpeedController(npc.route, dt=self.config.fixed_delta_s), scene.conflict_zone,
                        min_ttc_s=self.config.reactive_min_ttc_s,
                        occupancy_radius_m=self.config.reactive_occupancy_radius_m,
                        follow_gap_m=self.config.reactive_follow_gap_m,
                    )
            controls: dict[str, tuple[Any, str, str]] = {}
            total_ticks = int(round(self.config.run_duration_s / self.config.fixed_delta_s))
            with states_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=ACTOR_STATE_FIELDS)
                writer.writeheader()
                for step in range(1, total_ticks + 1):
                    time_s = step * self.config.fixed_delta_s
                    current_controller = prefix_controller if time_s - self.config.fixed_delta_s < intent.route_switch_s else ego_controller
                    ego_output = current_controller.step(actors["ego"], speed_from_schedule(intent.speed_schedule, time_s - self.config.fixed_delta_s))
                    ego_control = carla.VehicleControl(throttle=ego_output.throttle, brake=ego_output.brake, steer=ego_output.steer)
                    actors["ego"].apply_control(ego_control)
                    controls["ego"] = (ego_control, ego_output.reason, ego_output.mode)
                    for key, controller in reactive_controllers.items():
                        npc_spec = next(npc for npc in scene.npcs if npc.actor_key == key)
                        output = controller.step(actors[key], actors["ego"], npc_spec.tm_speed_mps)
                        control = carla.VehicleControl(throttle=output.throttle, brake=output.brake, steer=output.steer)
                        actors[key].apply_control(control)
                        controls[key] = (control, output.reason, output.mode)
                    self.environment.world.tick()
                    snapshot = self.environment.world.get_snapshot()
                    snapshot_time = float(snapshot.timestamp.elapsed_seconds)
                    if int(snapshot.frame) != int(initial_snapshot.frame) + step or abs(snapshot_time - float(initial_snapshot.timestamp.elapsed_seconds) - time_s) > 0.002:
                        raise ExperimentError("Unexpected world ticks/time drift: another client may be advancing this dedicated server")
                    for spec in [scene.ego, *scene.npcs]:
                        actor = actors[spec.actor_key]
                        control, reason, mode = controls.get(spec.actor_key, (actor.get_control(), "tm_route", "tm_default"))
                        writer.writerow(_row_for_actor(
                            run_id=run_id, scene=scene, profile=profile, intent=intent_id, repeat=repeat, seed=seed,
                            tick=int(snapshot.frame), time_s=time_s, actor_key=spec.actor_key, actor_role=spec.role,
                            simulation_time_s=snapshot_time,
                            actor=actor, control=control, collision=self.environment.collided(actor),
                            reaction_reason=reason, controller_mode=mode,
                        ))
            status = "complete"
            LOG.info("Completed %s seed=%d", run_id, seed)
        except Exception as exc:
            error = str(exc)
            LOG.exception("Run %s failed", run_id)
            if states_path.exists():
                states_path.unlink()
        finally:
            metadata = {
                "run_id": run_id, "status": status, "error": error, "scene_id": scene.scene_id,
                "category": scene.category, "profile": profile, "intent": intent_id, "repeat": repeat, "seed": seed,
                "created_at_utc": datetime.now(timezone.utc).isoformat(), "initial_state_checksum": _actor_checksum([scene.ego, *scene.npcs]),
                "initial_validation_messages": setup_messages, "intent_trigger_s": intent.trigger_s,
                "initial_states": locals().get("initial_states", {}),
                "actual_initial_state_checksum": config_hash(locals().get("initial_states", {})),
                "initial_frame": int(initial_snapshot.frame) if "initial_snapshot" in locals() else None,
                "initial_simulation_time_s": float(initial_snapshot.timestamp.elapsed_seconds) if "initial_snapshot" in locals() else None,
                "config_hash": self.effective_hash, "catalog_hash": self.catalog_hash,
                "implementation_hash": self.code_hash,
                "states_sha256": hashlib.sha256(states_path.read_bytes()).hexdigest() if states_path.exists() else "",
                "collision_events": list(self.environment._collision_events),
                "actor_id_map": {key: int(actor.id) for key, actor in actors.items() if getattr(actor, "is_alive", False)},
                "blueprints": {spec.actor_key: spec.blueprint for spec in [scene.ego, *scene.npcs]},
                "provenance": self.environment.provenance(),
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.environment.cleanup_fixture()
        return {
            "run_id": run_id, "status": status, "error": error, "seed": seed,
            "states_path": str(states_path), "metadata_path": str(metadata_path),
        }


def read_complete_state_files(output_dir: str | Path, *, catalog_hash: str | None = None, configuration_hash: str | None = None) -> Any:
    import pandas as pd
    root = Path(output_dir) / "runs"
    files = []
    for path in sorted(root.glob("*/*/*/rep_*/states.csv")) if root.exists() else []:
        metadata_path = path.parent / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if catalog_hash is not None and metadata.get("catalog_hash") != catalog_hash:
                raise ExperimentError(f"Catalog mismatch in stored data: {metadata_path}; use a separate output directory")
            if configuration_hash is not None and metadata.get("config_hash") != configuration_hash:
                raise ExperimentError(f"Simulation configuration mismatch in stored data: {metadata_path}")
            if metadata.get("status") == "complete" and metadata.get("states_sha256") == hashlib.sha256(path.read_bytes()).hexdigest():
                files.append(path)
    if not files:
        return pd.DataFrame(columns=ACTOR_STATE_FIELDS)
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
