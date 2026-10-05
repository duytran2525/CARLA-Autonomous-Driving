"""Small deterministic route and reactive-yield controllers.

They intentionally use CARLA ground truth.  ``reactive_yield_v1`` is an
experimental oracle controller, not a claim about normal Traffic Manager
behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

from .scenario_catalog import ConflictZone, SpeedPhase, TransformSpec


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def speed_mps(actor: Any) -> float:
    velocity = actor.get_velocity()
    return math.sqrt(float(velocity.x) ** 2 + float(velocity.y) ** 2 + float(velocity.z) ** 2)


def distance_xy_points(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(float(ax) - float(bx), float(ay) - float(by))


@dataclass(frozen=True)
class ControllerOutput:
    throttle: float
    brake: float
    steer: float
    reason: str = "route_follow"
    mode: str = "scripted_route"


class RouteSpeedController:
    """Pure-pursuit steering and bounded PID speed control at a fixed dt."""

    def __init__(self, route: Sequence[TransformSpec], *, lookahead_m: float = 7.0, dt: float = 0.05) -> None:
        if len(route) < 2:
            raise ValueError("RouteSpeedController needs at least two route points.")
        self.route = tuple(route)
        self.lookahead_m = max(2.0, float(lookahead_m))
        self._last_index = 0
        self.dt = dt
        self._integral = 0.0
        self._previous_error = None

    def _target(self, actor: Any) -> TransformSpec:
        location = actor.get_location()
        candidates = range(self._last_index, len(self.route))
        nearest = min(candidates, key=lambda idx: distance_xy_points(location.x, location.y, self.route[idx].x, self.route[idx].y))
        self._last_index = max(self._last_index, nearest)
        for index in range(self._last_index, len(self.route)):
            point = self.route[index]
            if distance_xy_points(location.x, location.y, point.x, point.y) >= self.lookahead_m:
                return point
        return self.route[-1]

    def step(self, actor: Any, target_speed_mps: float) -> ControllerOutput:
        transform = actor.get_transform()
        location = transform.location
        target = self._target(actor)
        heading = math.radians(float(transform.rotation.yaw))
        target_heading = math.atan2(float(target.y) - float(location.y), float(target.x) - float(location.x))
        heading_error = math.atan2(math.sin(target_heading - heading), math.cos(target_heading - heading))
        distance = max(1.0, distance_xy_points(location.x, location.y, target.x, target.y))
        steer = clamp(math.atan2(2 * 2.85 * math.sin(heading_error), distance) / 0.70, -0.8, 0.8)
        error = float(target_speed_mps) - speed_mps(actor)
        self._integral = clamp(self._integral + error * self.dt, -3.0, 3.0)
        derivative = 0.0 if self._previous_error is None else (error - self._previous_error) / self.dt
        self._previous_error = error
        demand = 0.35 * error + 0.08 * self._integral + 0.005 * derivative
        throttle = clamp(demand, 0.0, 0.75)
        brake = clamp(-1.6 * demand, 0.0, 1.0)
        if target_speed_mps <= 0.05 and speed_mps(actor) < 0.15:
            brake = 1.0
            throttle = 0.0
        return ControllerOutput(throttle, brake, steer)


class ReactiveYieldController:
    """Route controller that yields to ego at an occupied conflict zone."""

    def __init__(
        self,
        route_controller: RouteSpeedController,
        conflict_zone: ConflictZone,
        *,
        min_ttc_s: float = 3.0,
        occupancy_radius_m: float = 6.0,
        follow_gap_m: float = 10.0,
    ) -> None:
        self.route_controller = route_controller
        self.zone = conflict_zone
        self.min_ttc_s = float(min_ttc_s)
        self.occupancy_radius_m = float(occupancy_radius_m)
        self.follow_gap_m = float(follow_gap_m)

    def _time_to_zone(self, actor: Any) -> float:
        location = actor.get_location()
        distance = distance_xy_points(location.x, location.y, self.zone.x, self.zone.y)
        vel = actor.get_velocity()
        closing_speed = ((self.zone.x - location.x) * vel.x + (self.zone.y - location.y) * vel.y) / max(distance, 0.1)
        return distance / closing_speed if closing_speed > 0.25 else math.inf

    def step(self, actor: Any, ego: Any, desired_speed_mps: float) -> ControllerOutput:
        ego_loc = ego.get_location()
        npc_loc = actor.get_location()
        ego_zone_distance = distance_xy_points(ego_loc.x, ego_loc.y, self.zone.x, self.zone.y)
        npc_zone_distance = distance_xy_points(npc_loc.x, npc_loc.y, self.zone.x, self.zone.y)
        ego_ttc = self._time_to_zone(ego)
        npc_ttc = self._time_to_zone(actor)
        actor_distance = distance_xy_points(ego_loc.x, ego_loc.y, npc_loc.x, npc_loc.y)
        yaw = math.radians(actor.get_transform().rotation.yaw)
        forward_gap = (ego_loc.x - npc_loc.x) * math.cos(yaw) + (ego_loc.y - npc_loc.y) * math.sin(yaw)
        lateral_gap = abs(-(ego_loc.x - npc_loc.x) * math.sin(yaw) + (ego_loc.y - npc_loc.y) * math.cos(yaw))

        target_speed = float(desired_speed_mps)
        reason = "no_yield_condition"
        if ego_zone_distance <= self.occupancy_radius_m and npc_zone_distance <= 18.0 and math.isfinite(npc_ttc):
            target_speed, reason = 0.0, "yield_ego_occupies_conflict_zone"
        elif npc_zone_distance <= 35.0 and math.isfinite(ego_ttc) and math.isfinite(npc_ttc) and abs(ego_ttc - npc_ttc) <= self.min_ttc_s:
            target_speed, reason = 0.0, "yield_conflicting_ttc"
        elif 0 < forward_gap <= self.follow_gap_m and lateral_gap < 2.0 and speed_mps(ego) < speed_mps(actor):
            target_speed, reason = min(target_speed, max(0.0, speed_mps(ego) - 0.5)), "yield_closing_gap"

        output = self.route_controller.step(actor, target_speed)
        return ControllerOutput(output.throttle, output.brake, output.steer, reason, "reactive_yield_v1")


def speed_from_schedule(phases: Sequence[SpeedPhase], time_s: float) -> float:
    for phase in phases:
        if time_s >= phase.start_s and (phase.end_s is None or time_s < phase.end_s):
            return phase.speed_mps
    return phases[-1].speed_mps
