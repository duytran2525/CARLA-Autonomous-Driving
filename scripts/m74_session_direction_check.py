"""M74: is the "26 above / 1 below" session difference real or an artifact of the comparison?

Reads the two published scene_signal_metrics.csv files only (no resampling, no CARLA).
  1. reproduce the published comparison: session-2 point estimate vs session-1 bootstrap CI;
  2. swap the roles: session-1 point estimate vs session-2 bootstrap CI;
  3. compare the two point estimates directly (no CI involved).
A real "session 2 is noisier" effect predicts: (1) above, (2) below, (3) s2 > s1 in most cells.
A comparison artifact predicts: (1) above, (2) above again, (3) about half.

Usage: python -I scripts/m74_session_direction_check.py <s1 scene_signal_metrics.csv> <s2 scene_signal_metrics.csv>
"""
import sys
from math import comb

import pandas as pd

KEYS = ["scene_id", "profile", "signal"]


def sign_p(k, n):
    """two-sided exact binomial p-value for k successes of n at p=0.5"""
    tail = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main(s1_path, s2_path):
    s1, s2 = pd.read_csv(s1_path), pd.read_csv(s2_path)
    m = s1.merge(s2, on=KEYS, suffixes=("_s1", "_s2"), validate="one_to_one")
    print(f"rows={len(m)} (scene x profile x signal)")
    for metric in ("within", "between", "ratio"):
        a, b = m[f"{metric}_s1"], m[f"{metric}_s2"]
        fwd_hi = int((b > m[f"{metric}_ci_high_s1"]).sum()); fwd_lo = int((b < m[f"{metric}_ci_low_s1"]).sum())
        rev_hi = int((a > m[f"{metric}_ci_high_s2"]).sum()); rev_lo = int((a < m[f"{metric}_ci_low_s2"]).sum())
        up = int((b > a).sum()); n = int((b != a).sum())
        print(f"\n[{metric}]")
        print(f" 1. s2 point vs s1 CI : above={fwd_hi} below={fwd_lo}")
        print(f" 2. s1 point vs s2 CI : above={rev_hi} below={rev_lo}")
        print(f" 3. s2 > s1 point     : {up}/{n}  sign-test p={sign_p(up, n):.3f}  median s2/s1={float((b / a).median()):.3f}")
        # one unit per scene x profile (signals of one scene are not independent)
        pos = m[m.signal == "position"]
        up_pos = int((pos[f"{metric}_s2"] > pos[f"{metric}_s1"]).sum())
        print(f"    position only     : {up_pos}/{len(pos)}  sign-test p={sign_p(up_pos, len(pos)):.3f}")
        for profile, g in m.groupby("profile"):
            print(f"    {profile:18s}: s2>s1 in {int((g[f'{metric}_s2'] > g[f'{metric}_s1']).sum())}/{len(g)}, median s2/s1={float((g[f'{metric}_s2'] / g[f'{metric}_s1']).median()):.3f}")
    # how wide are the published within-CIs, and where does the point estimate sit inside its own CI
    rel_lo = ((m.within_s1 - m.within_ci_low_s1) / m.within_s1).median()
    rel_hi = ((m.within_ci_high_s1 - m.within_s1) / m.within_s1).median()
    own_above = int((m.within_s1 > m.within_ci_high_s1).sum())
    print(f"\n[shape of the published within CI, session 1] median distance point->low = {rel_lo:.2f} x point, point->high = {rel_hi:.2f} x point")
    print(f" session-1 point estimate above its OWN CI upper bound in {own_above}/{len(m)} rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
