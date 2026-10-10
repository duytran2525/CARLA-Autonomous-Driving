"""M74 offline re-analysis of the 1b raw runs (read-only; no CARLA).

Answers three owed checks from the M74 report (revised 2026-10-10):
  A. do the repeats of one cell start after a different number of pre-record ticks?
  B. within-session noise p90 with a run-level bootstrap CI (45 pairs are not independent);
  C. is cross-session noise larger than within-session noise, cell by cell?

Usage: python -I scripts/m74_offline_reanalysis.py <session1_runs> <session2_runs> <out.json>
"""
import csv, itertools, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np

DT = 0.05
N_BOOT = 2000
RNG = np.random.default_rng(20261010)


def load_run(rep_dir: Path):
    actors = defaultdict(list)
    with (rep_dir / "states.csv").open(newline="") as f:
        for r in csv.DictReader(f):
            actors[r["actor_key"]].append((float(r["x"]), float(r["y"])))
    meta = json.loads((rep_dir / "metadata.json").read_text(encoding="utf-8"))
    return {k: np.array(v) for k, v in actors.items()}, meta


def max_dpos(a, b):
    """max 2D position difference over shared actors and shared ticks (row order = tick)."""
    best = 0.0
    for key in a.keys() & b.keys():
        n = min(len(a[key]), len(b[key]))
        best = max(best, float(np.hypot(*(a[key][:n] - b[key][:n]).T).max()))
    return best


def load_session(root: Path):
    cells = {}
    for profile in sorted(p for p in root.iterdir() if p.is_dir()):
        for scene in sorted(p for p in profile.iterdir() if p.is_dir()):
            for intent in sorted(p for p in scene.iterdir() if p.is_dir()):
                reps = sorted(d for d in intent.glob("rep_*") if (d / "states.csv").exists() and (d / "metadata.json").exists())
                if len(reps) >= 2:
                    cells[(profile.name, scene.name, intent.name)] = [load_run(d) for d in reps]
    return cells


def boot_p90(dist):
    """Run-level bootstrap of the p90 over pairs of distinct runs. dist = symmetric n x n matrix."""
    n = len(dist)
    iu = np.triu_indices(n, 1)
    point = float(np.percentile(dist[iu], 90))
    draws = []
    for _ in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        sub = dist[np.ix_(idx, idx)]
        keep = idx[:, None] != idx[None, :]  # a run paired with its own copy is not a pair
        vals = sub[keep]
        if vals.size:
            draws.append(np.percentile(vals, 90))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point, float(lo), float(hi)


def within(runs):
    n = len(runs)
    dist = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        dist[i, j] = dist[j, i] = max_dpos(runs[i][0], runs[j][0])
    return dist


def main(s1_root, s2_root, out_path):
    s1, s2 = load_session(Path(s1_root)), load_session(Path(s2_root))
    rows = []
    for cell in sorted(s1.keys() & s2.keys()):
        r1, r2 = s1[cell], s2[cell]
        d1, d2 = within(r1), within(r2)
        cross = np.array([[max_dpos(a[0], b[0]) for b in r2] for a in r1])
        # same repeat index = same registered seed
        by_rep2 = {m["repeat"]: k for k, (_, m) in enumerate(r2)}
        same_seed = [cross[i, by_rep2[m["repeat"]]] for i, (_, m) in enumerate(r1)
                     if m["repeat"] in by_rep2 and m["seed"] == r2[by_rep2[m["repeat"]]][1]["seed"]]
        ticks1 = sorted({round(m["initial_simulation_time_s"] / DT) for _, m in r1})
        ticks2 = sorted({round(m["initial_simulation_time_s"] / DT) for _, m in r2})
        p1, p2 = boot_p90(d1), boot_p90(d2)
        iu1, iu2 = np.triu_indices(len(r1), 1), np.triu_indices(len(r2), 1)
        rows.append({
            "profile": cell[0], "scene": cell[1], "intent": cell[2], "n1": len(r1), "n2": len(r2),
            "prerecord_ticks_s1": ticks1, "prerecord_ticks_s2": ticks2,
            "within_s1_p90": p1[0], "within_s1_p90_ci": p1[1:], "within_s1_median": float(np.median(d1[iu1])),
            "within_s2_p90": p2[0], "within_s2_p90_ci": p2[1:], "within_s2_median": float(np.median(d2[iu2])),
            "cross_p90": float(np.percentile(cross, 90)), "cross_median": float(np.median(cross)),
            "cross_same_seed_median": float(np.median(same_seed)) if same_seed else None,
            "n_same_seed": len(same_seed),
        })
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(rows, indent=1), encoding="utf-8")

    n = len(rows)
    vary1 = sum(len(r["prerecord_ticks_s1"]) > 1 for r in rows)
    vary2 = sum(len(r["prerecord_ticks_s2"]) > 1 for r in rows)
    cross_gt_both = sum(r["cross_median"] > max(r["within_s1_median"], r["within_s2_median"]) for r in rows)
    cross_lt_both = sum(r["cross_median"] < min(r["within_s1_median"], r["within_s2_median"]) for r in rows)
    s2_gt_s1 = sum(r["within_s2_median"] > r["within_s1_median"] for r in rows)
    disjoint_hi = sum(r["within_s2_p90_ci"][0] > r["within_s1_p90_ci"][1] for r in rows)
    disjoint_lo = sum(r["within_s2_p90_ci"][1] < r["within_s1_p90_ci"][0] for r in rows)
    width = np.median([(r["within_s1_p90_ci"][1] - r["within_s1_p90_ci"][0]) / max(r["within_s1_p90"], 1e-9) for r in rows])
    print(f"cells={n}")
    print(f"A. cells whose repeats start after different pre-record tick counts: s1={vary1}/{n}, s2={vary2}/{n}")
    print(f"   tick counts seen: s1={sorted({t for r in rows for t in r['prerecord_ticks_s1']})} s2={sorted({t for r in rows for t in r['prerecord_ticks_s2']})}")
    print(f"B. median relative width of the 95% CI of within-session p90 (s1): {width:.2f}")
    print(f"C. within-session median noise higher in s2 than s1: {s2_gt_s1}/{n}")
    print(f"   p90 CIs disjoint: s2 above s1 in {disjoint_hi}, s2 below s1 in {disjoint_lo}")
    print(f"   cross-session median > both within medians: {cross_gt_both}/{n}; < both: {cross_lt_both}/{n}")
    by_profile = defaultdict(list)
    for r in rows:
        by_profile[r["profile"]].append(r)
    for profile, rs in by_profile.items():
        print(f"   {profile}: median over cells of within_s1 p90={np.median([r['within_s1_p90'] for r in rs]):.3f} m, "
              f"within_s2 p90={np.median([r['within_s2_p90'] for r in rs]):.3f} m, cross p90={np.median([r['cross_p90'] for r in rs]):.3f} m")


if __name__ == "__main__":
    main(*sys.argv[1:4])
