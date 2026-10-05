"""Statistics for the NPC counterfactual-response experiment."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import itertools
import hashlib
import math

import numpy as np
import pandas as pd


SIGNALS: Mapping[str, tuple[str, str]] = {
    "position": ("x", "y"),
    "velocity": ("vx", "vy"),
    "acceleration": ("ax", "ay"),
}


@dataclass(frozen=True)
class MetricsConfig:
    fixed_delta_s: float = 0.05
    analysis_start_offset_s: float = -1.0
    analysis_end_offset_s: float = 10.0
    bootstrap_samples: int = 2000
    permutation_samples: int = 2000
    random_seed: int = 20261002
    floors: Mapping[str, float] | None = None
    absolute_effect_thresholds: Mapping[str, float] | None = None

    def __post_init__(self):
        if self.bootstrap_samples < 1 or self.permutation_samples < 1 or self.fixed_delta_s <= 0:
            raise MetricsError("Resampling counts and fixed dt must be positive.")

    def floor(self, signal: str) -> float:
        return float((self.floors or {"position": 0.05, "velocity": 0.05, "acceleration": 0.10})[signal])

    def threshold(self, signal: str) -> float:
        return float((self.absolute_effect_thresholds or {"position": 0.5, "velocity": 0.25, "acceleration": 0.5})[signal])


class MetricsError(ValueError):
    pass


def rmse_time(left: np.ndarray, right: np.ndarray) -> float:
    """RMS Euclidean difference for [time, component] trajectories."""
    delta = np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
    return float(np.sqrt(np.mean(np.sum(delta * delta, axis=-1))))


def between_within(data: np.ndarray) -> tuple[float, float]:
    """Return B and W for [intent, repeat, time, component] values."""
    if data.ndim != 4 or data.shape[0] != 3 or data.shape[1] < 2 or not np.isfinite(data).all():
        raise MetricsError("Expected data with shape [3 intents, >=2 repeats, time, component].")
    condition_means = data.mean(axis=1)
    between = np.mean([
        rmse_time(condition_means[i], condition_means[j])
        for i, j in itertools.combinations(range(condition_means.shape[0]), 2)
    ])
    within_values = [
        rmse_time(data[intent, repeat], condition_means[intent])
        for intent in range(data.shape[0])
        for repeat in range(data.shape[1])
    ]
    return float(between), float(np.mean(within_values))


def ratio_between_within(between: float, within: float, floor: float) -> float:
    return float(between / max(float(within), float(floor)))


def _bootstrap_distribution(data: np.ndarray, floor: float, samples: int, rng: np.random.Generator) -> np.ndarray:
    repeats = data.shape[1]
    estimates = np.empty((samples, 3), dtype=float)
    for index in range(samples):
        indices = rng.integers(0, repeats, size=repeats)
        sampled = data[:, indices]
        between, within = between_within(sampled)
        estimates[index] = (between, within, ratio_between_within(between, within, floor))
    return estimates


def paired_permutation_pvalue(data: np.ndarray, observed_between: float, samples: int, rng: np.random.Generator) -> float:
    """Permutation test shuffling intent labels inside each matched repeat/seed."""
    larger_or_equal = 0
    for _ in range(samples):
        permuted = np.empty_like(data)
        for repeat in range(data.shape[1]):
            permutation = rng.permutation(data.shape[0])
            permuted[:, repeat] = data[permutation, repeat]
        candidate, _ = between_within(permuted)
        larger_or_equal += candidate >= observed_between - 1e-12
    return float((larger_or_equal + 1) / (samples + 1))


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Return monotone BH adjusted q-values in original order."""
    count = len(p_values)
    if not count:
        return []
    order = np.argsort(np.asarray(p_values, dtype=float))
    adjusted = np.empty(count, dtype=float)
    running = 1.0
    for rank in range(count, 0, -1):
        original_index = int(order[rank - 1])
        running = min(running, float(p_values[original_index]) * count / rank)
        adjusted[original_index] = running
    return [float(value) for value in adjusted]


def classify_scene(signal_rows: Sequence[Mapping[str, Any]], config: MetricsConfig) -> tuple[str, str]:
    """Classify one scene/profile using already FDR-adjusted aggregate metrics."""
    clear = [
        row for row in signal_rows
        if float(row["ratio_ci_low"]) >= 3.0
        and float(row["between"]) >= config.threshold(str(row["signal"]))
        and float(row["q_value"]) < 0.05
    ]
    if clear:
        return "clear_response", "effect_exceeds_noise"
    unchanged = [
        row for row in signal_rows
        if float(row["ratio_ci_high"]) < 1.5
        and float(row["between"]) < config.threshold(str(row["signal"]))
    ]
    if len(unchanged) == len(SIGNALS):
        return "almost_unchanged", "all_effects_below_noise_and_absolute_threshold"
    if all(float(row["between"]) < config.threshold(str(row["signal"])) for row in signal_rows):
        return "inconclusive", "effect_below_absolute_threshold"
    physical = [row for row in signal_rows if float(row["between"]) >= config.threshold(str(row["signal"]))]
    if all(float(row["ratio"]) < 3 for row in physical if "ratio" in row) and all("ratio" in row for row in physical):
        return "inconclusive", "noise_dominates_effect"
    if any(float(row["ratio_ci_low"]) >= 3 and float(row["q_value"]) >= .05 for row in physical):
        return "inconclusive", "insufficient_statistical_evidence_after_fdr"
    return "inconclusive", "noise_or_uncertain_effect"


def _analysis_rows(states: pd.DataFrame, trigger_s: float, config: MetricsConfig) -> pd.DataFrame:
    required = {"intent", "repeat", "actor_key", "relative_time_s", *[column for pair in SIGNALS.values() for column in pair]}
    missing = required - set(states.columns)
    if missing:
        raise MetricsError(f"Raw state data misses columns: {sorted(missing)}")
    start = trigger_s + config.analysis_start_offset_s
    end = trigger_s + config.analysis_end_offset_s
    rows = states[(states["relative_time_s"] >= start - 1e-6) & (states["relative_time_s"] <= end + 1e-6)].copy()
    rows["analysis_tick"] = np.rint((rows["relative_time_s"] - start) / config.fixed_delta_s).astype(int)
    if not np.allclose(rows.relative_time_s, start + rows.analysis_tick * config.fixed_delta_s, atol=1e-6, rtol=0):
        raise MetricsError("State times are not aligned to the configured fixed tick.")
    expected = set(range(int(round((end - start) / config.fixed_delta_s)) + 1))
    if set(rows.analysis_tick) != expected:
        raise MetricsError("Analysis window has missing ticks or is shorter than the configured window.")
    if rows.duplicated(["intent", "repeat", "actor_key", "analysis_tick"]).any():
        raise MetricsError("Duplicate actor/tick rows in a run.")
    return rows


def _tensor_for_actor(
    rows: pd.DataFrame,
    *,
    actor_key: str,
    intents: Sequence[str],
    repeats: Sequence[int],
    columns: tuple[str, str],
) -> np.ndarray:
    selected = rows[rows["actor_key"] == actor_key]
    expected_ticks = set(int(value) for value in rows.analysis_tick)
    trajectories: list[list[np.ndarray]] = []
    for intent in intents:
        by_repeat: list[np.ndarray] = []
        for repeat in repeats:
            run = selected[(selected["intent"] == intent) & (selected["repeat"] == repeat)].sort_values("analysis_tick")
            ticks = set(int(value) for value in run["analysis_tick"].tolist())
            if ticks != expected_ticks:
                raise MetricsError(f"Missing/misaligned ticks for actor={actor_key}, intent={intent}, repeat={repeat}.")
            if not ticks:
                raise MetricsError(f"No analysis rows for actor={actor_key}, intent={intent}, repeat={repeat}.")
            by_repeat.append(run.loc[:, list(columns)].to_numpy(dtype=float))
        trajectories.append(by_repeat)
    return np.asarray(trajectories, dtype=float)


def compute_scene_profile_metrics(
    states: pd.DataFrame,
    *,
    scene_id: str,
    profile: str,
    category: str,
    trigger_s: float,
    participant_keys: Sequence[str],
    intents: Sequence[str],
    config: MetricsConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute per-actor and aggregate scene metrics from complete run states."""
    subset = states[(states["scene_id"] == scene_id) & (states["profile"] == profile)].copy()
    repeats = sorted(int(value) for value in subset["repeat"].drop_duplicates().tolist())
    if len(intents) != 3 or len(repeats) < 2:
        raise MetricsError(f"{scene_id}/{profile} needs 3 intents and >=2 completed repeats.")
    rows = _analysis_rows(subset, trigger_s, config)
    if "seed" in subset:
        seeds = subset[["intent", "repeat", "seed"]].drop_duplicates()
        if seeds.groupby("repeat")["seed"].nunique().ne(1).any() or seeds.groupby(["intent", "repeat"]).size().ne(1).any():
            raise MetricsError("Intent runs do not share a paired seed per repetition.")
    actor_rows: list[dict[str, Any]] = []
    aggregate_inputs: dict[str, list[np.ndarray]] = {signal: [] for signal in SIGNALS}
    seed_base = int.from_bytes(hashlib.sha256(f"{scene_id}/{profile}/{config.random_seed}".encode()).digest()[:4], "big")

    for actor_index, actor_key in enumerate(participant_keys):
        for signal_index, (signal, columns) in enumerate(SIGNALS.items()):
            tensor = _tensor_for_actor(rows, actor_key=actor_key, intents=intents, repeats=repeats, columns=columns)
            between, within = between_within(tensor)
            rng = np.random.default_rng(seed_base + actor_index * 97 + signal_index)
            boot = _bootstrap_distribution(tensor, config.floor(signal), config.bootstrap_samples, rng)
            p_value = paired_permutation_pvalue(tensor, between, config.permutation_samples, rng)
            means = tensor.mean(axis=1)
            pair_metrics = [dict(intent_a=intents[i], intent_b=intents[j], between=rmse_time(means[i], means[j])) for i, j in itertools.combinations(range(3), 2)]
            actor_rows.append({
                "scene_id": scene_id, "category": category, "profile": profile, "actor_key": actor_key,
                "signal": signal, "between": between, "within": within,
                "ratio": ratio_between_within(between, within, config.floor(signal)),
                "between_ci_low": float(np.quantile(boot[:, 0], 0.025)), "between_ci_high": float(np.quantile(boot[:, 0], 0.975)),
                "within_ci_low": float(np.quantile(boot[:, 1], 0.025)), "within_ci_high": float(np.quantile(boot[:, 1], 0.975)),
                "ratio_ci_low": float(np.quantile(boot[:, 2], 0.025)),
                "ratio_ci_high": float(np.quantile(boot[:, 2], 0.975)), "p_value": p_value,
                "n_repeats": len(repeats), "n_ticks": int(tensor.shape[2]),
                "intent_pairs": pair_metrics,
            })
            aggregate_inputs[signal].append(tensor)

    aggregate_rows: list[dict[str, Any]] = []
    for signal_index, (signal, tensors) in enumerate(aggregate_inputs.items()):
        # RMS over actors is the pre-specified scene-level aggregation.
        pairs = [between_within(tensor) for tensor in tensors]
        between = float(math.sqrt(np.mean([value[0] ** 2 for value in pairs])))
        within = float(math.sqrt(np.mean([value[1] ** 2 for value in pairs])))
        rng = np.random.default_rng(seed_base + 10000 + signal_index)
        bootstrap = np.empty((config.bootstrap_samples, 3), dtype=float)
        permutation_between = np.empty(config.permutation_samples, dtype=float)
        repeats_count = tensors[0].shape[1]
        for draw in range(config.bootstrap_samples):
            sampled_pairs = []
            indices = rng.integers(0, repeats_count, size=repeats_count)
            for tensor in tensors:
                sampled = tensor[:, indices]
                sampled_pairs.append(between_within(sampled))
            sampled_b = math.sqrt(np.mean([value[0] ** 2 for value in sampled_pairs]))
            sampled_w = math.sqrt(np.mean([value[1] ** 2 for value in sampled_pairs]))
            bootstrap[draw] = (sampled_b, sampled_w, ratio_between_within(sampled_b, sampled_w, config.floor(signal)))
        for draw in range(config.permutation_samples):
            values = []
            permutations = [rng.permutation(3) for _ in range(repeats_count)]
            for tensor in tensors:
                shuffled = np.empty_like(tensor)
                for repeat in range(repeats_count):
                    shuffled[:, repeat] = tensor[permutations[repeat], repeat]
                values.append(between_within(shuffled)[0])
            permutation_between[draw] = math.sqrt(np.mean(np.square(values)))
        p_value = float((np.count_nonzero(permutation_between >= between - 1e-12) + 1) / (config.permutation_samples + 1))
        aggregate_rows.append({
            "scene_id": scene_id, "category": category, "profile": profile, "actor_key": "__scene_rms__",
            "signal": signal, "between": between, "within": within,
            "ratio": ratio_between_within(between, within, config.floor(signal)),
            "between_ci_low": float(np.quantile(bootstrap[:, 0], 0.025)), "between_ci_high": float(np.quantile(bootstrap[:, 0], 0.975)),
            "within_ci_low": float(np.quantile(bootstrap[:, 1], 0.025)), "within_ci_high": float(np.quantile(bootstrap[:, 1], 0.975)),
            "ratio_ci_low": float(np.quantile(bootstrap[:, 2], 0.025)),
            "ratio_ci_high": float(np.quantile(bootstrap[:, 2], 0.975)), "p_value": p_value,
            "n_repeats": len(repeats), "n_ticks": int(tensors[0].shape[2]),
        })
    return actor_rows, aggregate_rows


def analyze_completed_runs(
    states: pd.DataFrame,
    scene_definitions: Iterable[Mapping[str, Any]],
    config: MetricsConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Analyze all completed scenes and return actor, signal, scene summary tables."""
    actor_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    for scene in scene_definitions:
        for profile in sorted(states[states["scene_id"] == scene["scene_id"]]["profile"].drop_duplicates().tolist()):
            try:
                required_repeats = scene.get("required_repeats")
                selected = states[(states.scene_id == scene["scene_id"]) & (states.profile == profile)]
                if required_repeats is not None:
                    expected = set(range(1, int(required_repeats)+1))
                    for intent in scene["intent_ids"]:
                        if set(selected[selected.intent == intent]["repeat"]) != expected:
                            raise MetricsError(f"Missing runs for intent {intent}; expected repetitions {sorted(expected)}.")
                actor, aggregate = compute_scene_profile_metrics(
                    states, scene_id=str(scene["scene_id"]), profile=str(profile), category=str(scene["category"]),
                    trigger_s=float(scene["trigger_s"]), participant_keys=list(scene["participant_keys"]),
                    intents=list(scene["intent_ids"]), config=config,
                )
            except MetricsError as exc:
                incomplete.append(dict(scene_id=scene["scene_id"], profile=profile, category=scene["category"], classification="incomplete", classification_reason=str(exc)))
                continue
            actor_rows.extend(actor)
            aggregate_rows.extend(aggregate)
    actor_frame = pd.DataFrame(actor_rows)
    aggregate_frame = pd.DataFrame(aggregate_rows)
    if aggregate_frame.empty:
        return actor_frame, aggregate_frame, pd.DataFrame(incomplete)
    # FDR families are fixed per NPC profile so finishing reactive runs cannot
    # retrospectively change the baseline decision made after its phase.
    for frame in (aggregate_frame, actor_frame):
        for _, indices in frame.groupby("profile").groups.items():
            frame.loc[indices, "q_value"] = benjamini_hochberg(frame.loc[indices, "p_value"].tolist())
    summaries: list[dict[str, Any]] = incomplete
    for (scene_id, profile), group in aggregate_frame.groupby(["scene_id", "profile"], sort=True):
        status, reason = classify_scene(group.to_dict("records"), config)
        summary = {"scene_id": scene_id, "profile": profile, "category": group.iloc[0]["category"], "classification": status, "classification_reason": reason,
                   "n_repeats": int(group.iloc[0]["n_repeats"]), "n_ticks": int(group.iloc[0]["n_ticks"])}
        for _, row in group.iterrows():
            signal = str(row["signal"])
            for key in ("between", "within", "ratio", "between_ci_low", "between_ci_high", "within_ci_low", "within_ci_high", "ratio_ci_low", "ratio_ci_high", "p_value", "q_value"):
                summary[f"{signal}_{key}"] = float(row[key])
        raw = states[(states.scene_id == scene_id) & (states.profile == profile)]
        summary["collision_run_count"] = int(raw.groupby(["intent", "repeat"])["collision"].max().sum()) if "collision" in raw else 0
        if "ego" in set(raw.actor_key):
            ego = raw[raw.actor_key == "ego"][["intent", "repeat", "relative_time_s", "x", "y"]]
            npc = raw[raw.actor_key != "ego"]
            joined = npc.merge(ego, on=["intent", "repeat", "relative_time_s"], suffixes=("", "_ego"))
            summary["minimum_ego_npc_distance_m"] = float(np.hypot(joined.x - joined.x_ego, joined.y - joined.y_ego).min())
            if summary["minimum_ego_npc_distance_m"] > 35 and status != "clear_response":
                summary["classification_reason"] = "scene_design_no_close_interaction"
        # Collisions remain valid observations; expose their presence to avoid
        # conflating collision impulses with deliberate agent braking.
        summary["collision_associated"] = summary["collision_run_count"] > 0
        summaries.append(summary)
    return actor_frame, aggregate_frame, pd.DataFrame(summaries)


def metrics_config_as_dict(config: MetricsConfig) -> dict[str, Any]:
    return asdict(config)
