"""One-time fixture authoring from CARLA OpenDRIVE; never used by the runner.

Run ``python -m experiments.ego_intent_response.discovery --xodr PATH`` to
print a pinned JSON catalog (JSON is also valid YAML). Review/preflight the
result before replacing the checked-in catalog.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def xy(wp):
    p = wp.transform.location
    return np.array([p.x, p.y], dtype=float)


def angle(a, b):
    return (b - a + 180) % 360 - 180


def advance(wp, distance, backwards=False):
    candidates = wp.previous(distance) if backwards else wp.next(distance)
    if not candidates:
        raise ValueError("Route ends before the pinned horizon")
    return min(candidates, key=lambda p: (abs(angle(wp.transform.rotation.yaw, p.transform.rotation.yaw)), p.road_id, p.lane_id, p.s))


def trace(wp, distance=160, backwards=False, step=4):
    result = [wp]
    for _ in range(int(distance / step)):
        wp = advance(wp, step, backwards)
        result.append(wp)
    return result


def point(wp):
    p, r = wp.transform.location, wp.transform.rotation
    return dict(x=round(p.x, 5), y=round(p.y, 5), z=round(p.z + 0.35, 5), yaw_deg=round(r.yaw, 5))


def actor(key, wp, speed, route):
    return dict(actor_key=key, role="ego" if key == "ego" else "critical_conflict", critical=key != "ego",
                blueprint="vehicle.tesla.model3" if key == "ego" else "vehicle.audi.tt",
                transform=point(wp), initial_speed_mps=speed, tm_speed_mps=speed, route=route)


def junction_paths(m, carla):
    junctions = {wp.get_junction().id: wp.get_junction() for wp in m.generate_waypoints(10) if wp.is_junction}
    result = []
    for jid, junction in sorted(junctions.items()):
        for a, b in sorted(junction.get_waypoints(carla.LaneType.Driving), key=lambda pair: (pair[0].road_id, pair[0].lane_id)):
            length = abs(b.s - a.s)
            if length < 8:
                continue
            middle = [a] + [m.get_waypoint_xodr(a.road_id, a.lane_id, float(s)) for s in np.linspace(a.s, b.s, max(3, math.ceil(length / 2)))[1:-1]] + [b]
            if any(wp is None for wp in middle):
                continue
            try:
                approach = list(reversed(trace(a, 36, True)))
                exit_path = trace(b, 80)
            except ValueError:
                continue
            turn = angle(a.transform.rotation.yaw, b.transform.rotation.yaw)
            result.append(dict(jid=jid, turn=turn, middle=middle, route=approach[:-1] + middle + exit_path[1:], start=approach[0], entry=a))
    return result


def conflict_pairs(paths, category):
    for left in paths:
        if category == "unprotected_left" and not -120 < left["turn"] < -45:
            continue
        if category == "cross_traffic" and abs(left["turn"]) > 20:
            continue
        for right in paths:
            if left["jid"] != right["jid"] or abs(right["turn"]) > 20:
                continue
            approach_angle = abs(angle(left["entry"].transform.rotation.yaw, right["entry"].transform.rotation.yaw))
            if category == "unprotected_left" and approach_angle < 150:
                continue
            if category == "cross_traffic" and not 65 < approach_angle < 115:
                continue
            ls, rs = left["middle"], right["middle"]
            distances = np.linalg.norm(np.array([xy(p) for p in ls])[:, None] - np.array([xy(p) for p in rs])[None], axis=-1)
            i, j = np.unravel_index(np.argmin(distances), distances.shape)
            if distances[i, j] < 1.4 and 0 < i < len(ls)-1 and 0 < j < len(rs)-1:
                yield left, right, (xy(ls[i]) + xy(rs[j])) / 2


def build_catalog(xodr: Path):
    import carla
    contents = xodr.read_text(encoding="utf-8")
    m = carla.Map("Town03", contents)
    bank, scenes = {}, []

    def save(name, route):
        bank[name] = [point(wp) for wp in route]
        return name

    ids = {
        "merge": ("merge_now", "wait_then_merge", "stay_lane"),
        "cut_in": ("change_now", "wait_then_change", "do_not_change"),
        "overtake_slow": ("pass_now", "follow_slow", "abort_pass"),
        "rear_follow": ("cruise", "brake_and_hold", "accelerate"),
        "unprotected_left": ("turn_now", "yield_then_turn", "do_not_turn"),
        "cross_traffic": ("go_now", "yield_then_go", "stop_before_crossing"),
    }
    prefixes = dict(merge="merge", cut_in="cutin", overtake_slow="overtake", rear_follow="rear", unprotected_left="left", cross_traffic="crossing")
    junctions = junction_paths(m, carla)
    for category in ("merge", "unprotected_left", "overtake_slow", "cross_traffic", "cut_in", "rear_follow"):
        pair = next(conflict_pairs(junctions, category), None) if category in ("unprotected_left", "cross_traffic") else None
        if category in ("unprotected_left", "cross_traffic") and pair is None:
            raise ValueError(f"No valid conflict pair for {category}")
        for variant in range(1, 5):
            scene_id = f"{prefixes[category]}_{variant:02d}"
            speed = (25 + variant * 2) / 3.6
            gap = 8 + variant * 2
            if pair:
                left, right, zone = pair
                ego_wp = left["start"]
                npc_wp = advance(right["start"], variant * 1.0)
                ego_route = left["route"]
                npc_route = trace(npc_wp, 40)[:-1] + right["middle"] + trace(right["middle"][-1], 120)[1:]
                # Pin a continuous NPC route by following its branch up to the
                # exact junction entry, then using that connector's centreline.
                npc_approach = list(reversed(trace(right["entry"], 36-variant*4, True)))
                npc_wp = npc_approach[0]
                npc_route = npc_approach[:-1] + right["middle"] + trace(right["middle"][-1], 80)[1:]
                stay_route = ego_route
                main_route = ego_route
            else:
                road = 3 if category == "cut_in" else 65
                start_s = 35 + variant if category == "cut_in" else 145 + variant
                ego_wp = m.get_waypoint_xodr(road, -2 if category == "overtake_slow" else -1, start_s)
                ego_route = trace(ego_wp, 180)
                parallel = ego_wp.get_left_lane() if category == "overtake_slow" else ego_wp.get_right_lane()
                if parallel is None or parallel.lane_type != carla.LaneType.Driving:
                    raise ValueError("Expected a parallel driving lane")
                parallel_route = trace(parallel, 180)
                stay_route = ego_route
                # Preserve a common prefix through trigger=3 s, lane transition
                # only after 28 m. Points remain on the two driving centrelines.
                main_route = ego_route[:8] + parallel_route[8:]
                if category == "rear_follow":
                    main_route = ego_route
                    npc_wp = advance(ego_wp, gap, True)
                elif category == "overtake_slow":
                    npc_wp = advance(ego_wp, 16 + variant*2)
                else:
                    npc_wp = advance(parallel, gap, True)
                npc_route = trace(npc_wp, 200)
                zone = xy(parallel_route[10] if category != "rear_follow" else ego_route[10])
            main_ref = save(scene_id + "_maneuver", main_route)
            stay_ref = save(scene_id + "_stay", stay_route)
            npc_ref = save(scene_id + "_npc", npc_route)
            if category == "rear_follow":
                speed = 30/3.6
            ego_spec = actor("ego", ego_wp, speed, stay_ref)
            npc_speed = 4.0 if category == "overtake_slow" else speed + 0.7
            npc_spec = actor("npc_conflict", npc_wp, npc_speed, npc_ref)
            intents = {}
            for index, intent_id in enumerate(ids[category]):
                phases = [dict(start_s=0.0, end_s=3.0, speed_mps=speed)]
                if index == 1 and category != "overtake_slow":
                    phases.extend([dict(start_s=3.0, end_s=6.0 if category != "merge" else 5.5, speed_mps=0.0), dict(start_s=6.0 if category != "merge" else 5.5, end_s=None, speed_mps=speed)])
                else:
                    target = speed
                    if index == 2:
                        target = 40/3.6 if category == "rear_follow" else 0.0 if pair else 2.0 if category == "overtake_slow" else speed
                    if index == 1 and category == "overtake_slow":
                        target = 4.0
                    phases.append(dict(start_s=3.0, end_s=None, speed_mps=target))
                intents[intent_id] = dict(display_name=intent_id, trigger_s=3.0, route=main_ref if index != 2 else stay_ref, speed_schedule=phases,
                                         route_switch_s=5.5 if category == "merge" and index == 1 else 6.0 if index == 1 else 3.0)
            if category == "overtake_slow":
                intents[ids[category][1]]["route"] = stay_ref
            scenes.append(dict(scene_id=scene_id, category=category, variant=variant, ego=ego_spec, npcs=[npc_spec], intents=intents,
                               traffic_light_state="Green", conflict_zone=dict(x=float(zone[0]), y=float(zone[1]), radius_m=5.0), interaction_distance_m=35.0))
    return dict(schema_version=1, town="Town03", opendrive_sha256=hashlib.sha256(contents.encode()).hexdigest(), route_bank=bank, scenes=scenes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xodr", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_catalog(args.xodr), separators=(",", ":")))
