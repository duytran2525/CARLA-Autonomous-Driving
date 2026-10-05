"""Write reproducible experiment tables and the human-facing conclusion."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
from html import escape
import json

import pandas as pd


def write_trajectory_plots(output_dir: str | Path, states: pd.DataFrame) -> list[Path]:
    """Optional dependency-free SVGs: global XY mean paths for each intent."""
    if states.empty:
        return []
    root = Path(output_dir) / "trajectory_plots"
    root.mkdir(parents=True, exist_ok=True)
    paths = []
    colors = ("#2563eb", "#dc2626", "#059669")
    for (scene, profile), runs in states.groupby(["scene_id", "profile"], sort=True):
        means = runs.groupby(["intent", "actor_key", "relative_time_s"], as_index=False)[["x", "y"]].mean()
        xmin, xmax = float(means.x.min()), float(means.x.max())
        ymin, ymax = float(means.y.min()), float(means.y.max())
        scale = min(640/max(xmax-xmin, 1), 400/max(ymax-ymin, 1))
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="540" viewBox="0 0 760 540">',
                 '<rect width="760" height="540" fill="white"/>',
                 f'<text x="40" y="28" font-family="sans-serif" font-size="18">{escape(str(scene))} / {escape(str(profile))}</text>']
        for index, (intent, rows) in enumerate(means.groupby("intent", sort=True)):
            color = colors[index % len(colors)]
            for actor, trajectory in rows.groupby("actor_key", sort=True):
                trajectory = trajectory.sort_values("relative_time_s")
                points = " ".join(f"{50+(row.x-xmin)*scale:.2f},{60+(ymax-row.y)*scale:.2f}" for row in trajectory.itertuples())
                dash = ' stroke-dasharray="6 3"' if actor != "ego" else ""
                parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash}><title>{escape(str(intent))}: {escape(str(actor))}</title></polyline>')
            parts.append(f'<text x="40" y="{480+index*18}" fill="{color}" font-family="sans-serif" font-size="13">{escape(str(intent))}</text>')
        parts += [f'<text x="380" y="480" font-family="sans-serif" font-size="12">Global XY (m); x={xmin:.1f}..{xmax:.1f}; y={ymin:.1f}..{ymax:.1f}</text>',
                  '<text x="380" y="500" font-family="sans-serif" font-size="12">Solid: ego; dashed: NPC; mean over repeats</text>', '</svg>']
        path = root / f"{scene}_{profile}.svg"
        path.write_text("\n".join(parts)+"\n", encoding="utf-8")
        paths.append(path)
    return paths


def _markdown_list(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "- Không có."
    return "\n".join(f"- `{row.scene_id}` ({row.profile}; {row.category})" for row in rows.itertuples())


def write_reports(
    output_dir: str | Path,
    *,
    actor_effects: pd.DataFrame,
    aggregate_effects: pd.DataFrame,
    summary: pd.DataFrame,
    provenance: Mapping[str, Any],
    baseline_only: bool = False,
) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    summary = summary.copy()
    for column in ("scene_id", "profile", "category", "classification", "classification_reason"):
        if column not in summary:
            summary[column] = pd.Series(dtype=str)
    effect_columns = ["scene_id", "category", "profile", "actor_key", "signal", "between", "within", "ratio",
                      "between_ci_low", "between_ci_high", "within_ci_low", "within_ci_high",
                      "ratio_ci_low", "ratio_ci_high", "p_value", "q_value", "n_repeats", "n_ticks"]
    if actor_effects.empty:
        actor_effects = pd.DataFrame(columns=effect_columns)
    if aggregate_effects.empty:
        aggregate_effects = pd.DataFrame(columns=effect_columns)
    paths = {
        "actor_effects": root / "actor_effects.csv",
        "intent_pair_metrics": root / "intent_pair_metrics.csv",
        "summary": root / "summary_by_scene.csv",
        "report": root / "response_report.md",
        "decision": root / "decision.json",
    }
    pairs = []
    for row in actor_effects.to_dict("records"):
        for pair in row.get("intent_pairs", []):
            pairs.append({**{k: row[k] for k in ("scene_id", "profile", "actor_key", "signal")}, **pair,
                          "within": row["within"], "ratio": pair["between"] / max(row["within"], 0.1 if row["signal"] == "acceleration" else 0.05)})
    actor_effects.drop(columns=["intent_pairs"], errors="ignore").to_csv(paths["actor_effects"], index=False)
    pd.DataFrame(pairs, columns=["scene_id", "profile", "actor_key", "signal", "intent_a", "intent_b", "between", "within", "ratio"]).to_csv(paths["intent_pair_metrics"], index=False)
    aggregate_effects.to_csv(root / "scene_signal_metrics.csv", index=False)
    summary.to_csv(paths["summary"], index=False)
    clear = summary[summary.get("classification", pd.Series(dtype=str)) == "clear_response"]
    unchanged = summary[summary.get("classification", pd.Series(dtype=str)) == "almost_unchanged"]
    inconclusive = summary[summary.get("classification", pd.Series(dtype=str)) == "inconclusive"]
    incomplete = summary[summary.get("classification", pd.Series(dtype=str)) == "incomplete"]
    baseline = summary[summary.get("profile", pd.Series(dtype=str)) == "tm_default"]
    baseline_clear_count = int((baseline.get("classification", pd.Series(dtype=str)) == "clear_response").sum())
    complete_baseline = len(baseline) == 24 and (baseline.classification != "incomplete").all() and (baseline.get("n_repeats", pd.Series(dtype=float)) >= 10).all()
    profile_decisions = {}
    for profile, rows in summary.groupby("profile") if not summary.empty else []:
        count = int((rows.classification == "clear_response").sum())
        complete = len(rows) == 24 and (rows.classification != "incomplete").all() and (rows.get("n_repeats", pd.Series(dtype=float)) >= 10).all()
        profile_decisions[profile] = dict(clear_response_count=count, matrix_complete=bool(complete), passes_half_scene_target=(count >= 12) if complete else None)
    decision = {
        "baseline_clear_response_count": baseline_clear_count,
        "baseline_target_count": 12,
        "baseline_passes_half_scene_target": (baseline_clear_count >= 12) if complete_baseline else None,
        "matrix_complete": len(profile_decisions) == 2 and all(d["matrix_complete"] for d in profile_decisions.values()),
        "profile_decisions": profile_decisions,
        "profiles": sorted(summary["profile"].drop_duplicates().tolist()) if not summary.empty else [],
        "provenance": dict(provenance),
    }
    paths["decision"].write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = f"""# NPC response to ego intent\n\nThis report compares fixed ego intent scripts within identical Town03 fixtures. `tm_default` is CARLA Traffic Manager. `reactive_yield_v1` is an oracle controller using CARLA ground truth TTC/gap/occupancy; it is not default CARLA behaviour.\n\n## Clearly responsive\n\n{_markdown_list(clear)}\n\n## Almost unchanged\n\n{_markdown_list(unchanged)}\n\n## Inconclusive\n\n{_markdown_list(inconclusive)}\n\n## Baseline decision\n\nTraffic Manager baseline: {baseline_clear_count}/24 clearly responsive scenes. Target: 12/24.\n"""
    report += "\n## Incomplete cells\n\n" + _markdown_list(incomplete) + "\n"
    if "collision_associated" in summary:
        collision_scenes = summary[summary.collision_associated.eq(True)]
        report += "\n## Collision-associated observations\n\n" + _markdown_list(collision_scenes) + "\n"
        report += "\nThese effects include collision impulses. They must not be interpreted as intentional agent reactions without inspecting pre-impact trajectories/controls.\n"
    if not complete_baseline:
        report += "\nThe full 24-scene, 10-repeat baseline is incomplete; no pass/fail conclusion is available.\n"
    report += "\n## Agent and analysis configuration\n\n```json\n" + json.dumps(dict(provenance), ensure_ascii=False, indent=2) + "\n```\n"
    if baseline_only and (baseline_clear_count < 12 or not complete_baseline):
        report += "\nBaseline is below the target. See `baseline_failure_notice.md` for the numeric diagnosis.\n"
    paths["report"].write_text(report, encoding="utf-8")
    if baseline_only and (baseline_clear_count < 12 or not complete_baseline):
        notices = []
        for row in baseline.itertuples():
            reason = str(getattr(row, "classification_reason", "unknown"))
            values = "; ".join(f"{signal}: B={getattr(row, signal+'_between',float('nan')):.3f}, W={getattr(row, signal+'_within',float('nan')):.3f}, R={getattr(row, signal+'_ratio',float('nan')):.2f}" for signal in ("position", "velocity", "acceleration"))
            notices.append(f"- `{row.scene_id}`: {reason}; {values}")
        failure_path = root / "baseline_failure_notice.md"
        failure_path.write_text(
            "# Baseline failure notice\n\n"
            f"Only {baseline_clear_count}/24 Town03 Traffic Manager scenes met the pre-registered response criterion.\n\n"
            "## Per-scene diagnostic\n\n" + "\n".join(notices) + "\n",
            encoding="utf-8",
        )
        paths["baseline_failure_notice"] = failure_path
    return paths
