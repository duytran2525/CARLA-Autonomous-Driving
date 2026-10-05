"""Pinned scene catalog and deterministic Town03 fixture helpers.

The experiment deliberately identifies actors by ``actor_key`` instead of
CARLA's run-local actor id.  Actor ids are saved as provenance only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
import hashlib
import json
import math

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared by project
    yaml = None


PROFILES = ("tm_default", "reactive_yield_v1")
ACTOR_STATE_FIELDS = (
    "run_id", "scene_id", "category", "profile", "intent", "repeat", "seed",
    "tick", "time_s", "relative_time_s", "actor_key", "actor_id", "actor_role",
    "actor_type", "x", "y", "z", "yaw_deg", "vx", "vy", "vz", "speed_mps",
    "ax", "ay", "az", "throttle", "brake", "steer", "hand_brake",
    "collision", "reaction_reason", "controller_mode",
)


class CatalogError(ValueError):
    """The catalog is malformed or cannot represent the intended experiment."""


@dataclass(frozen=True)
class TransformSpec:
    x: float
    y: float
    z: float = 0.3
    yaw_deg: float = 0.0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, label: str) -> "TransformSpec":
        try:
            result = cls(
                x=float(value["x"]), y=float(value["y"]), z=float(value.get("z", 0.3)),
                yaw_deg=float(value.get("yaw_deg", value.get("yaw", 0.0))),
            )
            if not all(math.isfinite(v) for v in result.as_dict().values()):
                raise ValueError("Nonfinite coordinate")
            return result
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogError(f"{label} needs numeric x/y[/z/yaw_deg].") from exc

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z, "yaw_deg": self.yaw_deg}


@dataclass(frozen=True)
class SpeedPhase:
    start_s: float
    end_s: float | None
    speed_mps: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, label: str) -> "SpeedPhase":
        try:
            start = float(value["start_s"])
            end_value = value.get("end_s")
            end = None if end_value is None else float(end_value)
            speed = float(value["speed_mps"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogError(f"{label} needs start_s, optional end_s, and speed_mps.") from exc
        if not all(math.isfinite(v) for v in (start, speed)) or (end is not None and not math.isfinite(end)) or start < 0 or (end is not None and end <= start) or speed < 0:
            raise CatalogError(f"{label} has invalid time or speed.")
        return cls(start, end, speed)


@dataclass(frozen=True)
class ActorSpec:
    actor_key: str
    role: str
    blueprint: str
    transform: TransformSpec
    initial_speed_mps: float
    route: tuple[TransformSpec, ...]
    tm_speed_mps: float
    critical: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, label: str) -> "ActorSpec":
        key = str(value.get("actor_key", "")).strip()
        role = str(value.get("role", "npc")).strip()
        blueprint = str(value.get("blueprint", "vehicle.tesla.model3")).strip()
        if not key or not role or not blueprint:
            raise CatalogError(f"{label} needs actor_key, role, and blueprint.")
        route_raw = value.get("route") or []
        if not isinstance(route_raw, list) or len(route_raw) < 2:
            raise CatalogError(f"{label}.route needs at least two fixed points.")
        route = tuple(TransformSpec.from_mapping(point, label=f"{label}.route") for point in route_raw)
        initial = TransformSpec.from_mapping(value.get("transform") or {}, label=f"{label}.transform")
        speed = float(value.get("initial_speed_mps", 0.0))
        tm_speed = float(value.get("tm_speed_mps", speed))
        if not math.isfinite(speed) or not math.isfinite(tm_speed) or speed < 0 or tm_speed < 0:
            raise CatalogError(f"{label} speed cannot be negative.")
        return cls(key, role, blueprint, initial, speed, route, tm_speed, bool(value.get("critical", False)))


@dataclass(frozen=True)
class IntentSpec:
    intent_id: str
    display_name: str
    route: tuple[TransformSpec, ...]
    speed_schedule: tuple[SpeedPhase, ...]
    trigger_s: float
    route_switch_s: float = 3.0

    @classmethod
    def from_mapping(cls, intent_id: str, value: Mapping[str, Any], *, label: str) -> "IntentSpec":
        name = str(value.get("display_name", intent_id)).strip()
        route_raw = value.get("route") or []
        if not isinstance(route_raw, list) or len(route_raw) < 2:
            raise CatalogError(f"{label}.route needs at least two fixed points.")
        phases_raw = value.get("speed_schedule") or []
        if not isinstance(phases_raw, list) or not phases_raw:
            raise CatalogError(f"{label}.speed_schedule cannot be empty.")
        phases = tuple(SpeedPhase.from_mapping(p, label=f"{label}.speed_schedule") for p in phases_raw)
        if phases[0].start_s != 0 or phases[-1].end_s is not None or any(a.end_s != b.start_s for a, b in zip(phases, phases[1:])):
            raise CatalogError(f"{label} speed schedule must cover time from zero without gaps/overlaps.")
        trigger_s = float(value.get("trigger_s", 3.0))
        if not math.isfinite(trigger_s) or trigger_s < 1.0:
            raise CatalogError(f"{label}.trigger_s must be at least one second.")
        if not math.isfinite(float(value.get("route_switch_s", trigger_s))) or float(value.get("route_switch_s", trigger_s)) < trigger_s:
            raise CatalogError(f"{label} route cannot switch before trigger.")
        return cls(
            intent_id=str(intent_id), display_name=name,
            route=tuple(TransformSpec.from_mapping(p, label=f"{label}.route") for p in route_raw),
            speed_schedule=phases, trigger_s=trigger_s, route_switch_s=float(value.get("route_switch_s", trigger_s)),
        )

    def speed_at(self, time_s: float) -> float:
        for phase in self.speed_schedule:
            if time_s >= phase.start_s and (phase.end_s is None or time_s < phase.end_s):
                return phase.speed_mps
        return self.speed_schedule[-1].speed_mps


@dataclass(frozen=True)
class ConflictZone:
    x: float
    y: float
    radius_m: float

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, label: str) -> "ConflictZone":
        try:
            zone = cls(float(value["x"]), float(value["y"]), float(value["radius_m"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogError(f"{label} needs x/y/radius_m.") from exc
        if not all(math.isfinite(v) for v in (zone.x, zone.y, zone.radius_m)) or zone.radius_m <= 0:
            raise CatalogError(f"{label}.radius_m must be positive.")
        return zone


@dataclass(frozen=True)
class SceneSpec:
    scene_id: str
    category: str
    variant: int
    ego: ActorSpec
    intents: dict[str, IntentSpec]
    npcs: tuple[ActorSpec, ...]
    conflict_zone: ConflictZone
    interaction_distance_m: float = 35.0
    traffic_light_state: str = "Green"

    @property
    def actor_keys(self) -> tuple[str, ...]:
        return (self.ego.actor_key,) + tuple(npc.actor_key for npc in self.npcs)

    @property
    def participant_keys(self) -> tuple[str, ...]:
        return tuple(npc.actor_key for npc in self.npcs)

    @property
    def critical_keys(self) -> tuple[str, ...]:
        return tuple(npc.actor_key for npc in self.npcs if npc.critical)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SceneSpec":
        scene_id = str(value.get("scene_id", "")).strip()
        category = str(value.get("category", "")).strip()
        if not scene_id or not category:
            raise CatalogError("Every scene needs scene_id and category.")
        ego = ActorSpec.from_mapping(value.get("ego") or {}, label=f"{scene_id}.ego")
        if ego.actor_key != "ego":
            raise CatalogError(f"{scene_id}.ego.actor_key must be 'ego'.")
        raw_intents = value.get("intents") or {}
        if not isinstance(raw_intents, Mapping) or len(raw_intents) != 3:
            raise CatalogError(f"{scene_id} must contain exactly three intents.")
        intents = {
            str(intent_id): IntentSpec.from_mapping(str(intent_id), payload, label=f"{scene_id}.intents.{intent_id}")
            for intent_id, payload in raw_intents.items()
        }
        if len({i.trigger_s for i in intents.values()}) != 1:
            raise CatalogError(f"{scene_id} intents must share the same trigger.")
        trigger = next(iter(intents.values())).trigger_s
        phase_boundaries = sorted({p.start_s for i in intents.values() for p in i.speed_schedule if p.start_s < trigger})
        if any(len({i.speed_at(t) for i in intents.values()}) != 1 for t in phase_boundaries):
            raise CatalogError(f"{scene_id} intents must share the same pre-trigger speed schedule.")
        raw_npcs = value.get("npcs") or []
        if not isinstance(raw_npcs, list) or not raw_npcs:
            raise CatalogError(f"{scene_id} needs at least one NPC fixture.")
        npcs = tuple(ActorSpec.from_mapping(npc, label=f"{scene_id}.npcs") for npc in raw_npcs)
        keys = [ego.actor_key] + [npc.actor_key for npc in npcs]
        if len(keys) != len(set(keys)):
            raise CatalogError(f"{scene_id} actor_key values must be unique.")
        if not any(npc.critical for npc in npcs):
            raise CatalogError(f"{scene_id} needs a critical NPC.")
        return cls(
            scene_id=scene_id, category=category, variant=int(value.get("variant", 0)), ego=ego,
            intents=intents, npcs=npcs,
            conflict_zone=ConflictZone.from_mapping(value.get("conflict_zone") or {}, label=f"{scene_id}.conflict_zone"),
            interaction_distance_m=float(value.get("interaction_distance_m", 35.0)),
            traffic_light_state=str(value.get("traffic_light_state", "Green")),
        )


@dataclass(frozen=True)
class ScenarioCatalog:
    town: str
    schema_version: int
    scenes: tuple[SceneSpec, ...]
    source_path: Path
    source_hash: str
    opendrive_sha256: str = ""

    def by_id(self, scene_id: str) -> SceneSpec:
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise KeyError(f"Unknown scene_id: {scene_id}")

    def select(self, scene_ids: Iterable[str] | None = None) -> tuple[SceneSpec, ...]:
        if scene_ids is None:
            return self.scenes
        wanted = {value.strip() for value in scene_ids if value.strip()}
        missing = wanted - {scene.scene_id for scene in self.scenes}
        if missing:
            raise CatalogError(f"Unknown requested scenes: {sorted(missing)}")
        return tuple(scene for scene in self.scenes if scene.scene_id in wanted)


def load_catalog(path: str | Path) -> ScenarioCatalog:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load the experiment catalog.")
    source = Path(path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Scene catalog not found: {source}")
    raw_bytes = source.read_bytes()
    try:
        raw = yaml.safe_load(raw_bytes) or {}
    except Exception as exc:
        raise CatalogError(f"Cannot parse catalog {source}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise CatalogError("Catalog root must be a mapping.")
    scenes_raw = raw.get("scenes") or []
    bank = raw.get("route_bank", {})
    if not isinstance(scenes_raw, list) or not isinstance(bank, Mapping) or any(not isinstance(s, Mapping) for s in scenes_raw):
        raise CatalogError("Catalog scenes must be a list of mappings and route_bank a mapping.")
    for scene in scenes_raw:
        for payload in [scene.get("ego", {}), *scene.get("npcs", []), *scene.get("intents", {}).values()]:
            if isinstance(payload.get("route"), str):
                route_id = payload["route"]
                if route_id not in bank:
                    raise CatalogError(f"Unknown pinned route: {route_id}")
                payload["route"] = bank[route_id]
    if not isinstance(scenes_raw, list):
        raise CatalogError("Catalog scenes must be a list.")
    scenes = tuple(SceneSpec.from_mapping(scene) for scene in scenes_raw)
    ids = [scene.scene_id for scene in scenes]
    if len(ids) != len(set(ids)):
        raise CatalogError("scene_id values must be unique.")
    categories = {scene.category for scene in scenes}
    required_categories = {"merge", "unprotected_left", "overtake_slow", "cross_traffic", "cut_in", "rear_follow"}
    if categories != required_categories:
        raise CatalogError("Catalog category names do not match the six experiment families.")
    if len(scenes) != 24:
        raise CatalogError(f"Catalog must contain 24 scenes, got {len(scenes)}.")
    if len(categories) != 6 or any(sum(scene.category == cat for scene in scenes) != 4 for cat in categories):
        raise CatalogError("Catalog must contain six categories with four scenes each.")
    return ScenarioCatalog(
        town=str(raw.get("town", "Town03")), schema_version=int(raw.get("schema_version", 1)),
        scenes=scenes, source_path=source, source_hash=hashlib.sha256(raw_bytes).hexdigest(),
        opendrive_sha256=str(raw.get("opendrive_sha256", "")),
    )


def config_hash(value: Mapping[str, Any]) -> str:
    """Stable config hash stored in each run's provenance metadata."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def distance_xy(a: TransformSpec, b: TransformSpec) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)
