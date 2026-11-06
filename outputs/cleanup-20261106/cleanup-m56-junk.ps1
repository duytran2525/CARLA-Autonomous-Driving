# M56 cleanup proposal (Claude, 2026-11-06) - RUN BY THE USER, not by Claude.
# Kept: every sealed native A/B (m56_io_ab_*, m56_v2_ab_*), every revision/preparation/compile folder that a kept revision
# or a document cites, every official pair evaluation, full suite 9. Before deleting a folder its file list (relative path
# + size) is written next to this script (manifest-<name>.tsv), so citations can still be traced.
#
# Tier 1 (default, ~0.5 GB): superseded/unused I/O work folders of 2026-10-26/27 and Python caches.
#   - revisions never used by an A/B: io_base, io_o0102 (v1.1 blocked prep), io_o0102b (pre-midpoint), io_o03 162806Z
#   - compile-only folders superseded by a later compile (incl. the 3 offline ones)
#   - preparations superseded (O03 pilot bugs 161332-161959; O01/O02 first two attempts)
#   - empty pair folders (115607Z, 172208Z)
#   - __pycache__ folders in the M56 worktrees (regenerated automatically)
# Tier 2 (only with -IncludeRegenerablePairs, ~3.6 GB): the v6-era pair evaluations of 2026-10-26 (070552Z ... 135120Z).
#   They are regenerable from the kept sealed A/B folders with native-v6-pair.py (M56_CODE=..\m56-v6); the v7
#   re-evaluation of the same episodes is kept (m56_v6_pair_20261026T142613Z).
# Usage (PowerShell):  powershell -ExecutionPolicy Bypass -File cleanup-m56-junk.ps1 [-IncludeRegenerablePairs]
param([switch]$IncludeRegenerablePairs)
$ErrorActionPreference = 'Stop'
$out = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'
$here = Join-Path $out 'cleanup-20261106'
$tier1 = @(
  'm56_c0_partial_io_base_20261026T162755Z', 'm56_c0_partial_io_o0102_20261027T031709Z',
  'm56_c0_partial_io_o0102b_20261027T032259Z', 'm56_c0_partial_io_o03_20261026T162806Z',
  'm56_io_compile_Town04_20261027T031717Z', 'm56_io_compile_Town04_20261027T032310Z',
  'm56_io_compile_Town05_20261027T031754Z', 'm56_io_compile_Town05_20261027T032432Z',
  'm56_io_compile_Town06_20261026T163229Z', 'm56_io_compile_Town06_20261026T163617Z',
  'm56_io_compile_Town06_offline-20261026T163435Z', 'm56_io_compile_Town06_offline-20261026T164340Z',
  'm56_io_compile_Town06_offline-20261026T164407Z',
  'm56_v2_prepare_Town06_20261026T161332Z', 'm56_v2_prepare_Town06_20261026T161514Z',
  'm56_v2_prepare_Town06_20261026T161731Z', 'm56_v2_prepare_Town06_20261026T161959Z',
  'm56_v2_prepare_Town04_20261027T031416Z', 'm56_v2_prepare_Town04_20261027T031914Z',
  'm56_v2_prepare_Town05_20261027T031549Z', 'm56_v2_prepare_Town05_20261027T032107Z',
  'm56_v6_pair_20261026T115607Z', 'm56_v6_pair_20261026T172208Z')
$tier2 = @('m56_v6_pair_20261026T070552Z', 'm56_v6_pair_20261026T100753Z', 'm56_v6_pair_20261026T104056Z',
  'm56_v6_pair_20261026T104859Z', 'm56_v6_pair_20261026T105649Z', 'm56_v6_pair_20261026T111353Z',
  'm56_v6_pair_20261026T115608Z', 'm56_v6_pair_20261026T125113Z', 'm56_v6_pair_20261026T131100Z',
  'm56_v6_pair_20261026T135120Z')
$targets = @($tier1 | ForEach-Object { Join-Path $out $_ } | Where-Object { Test-Path $_ })
if ($IncludeRegenerablePairs) { $targets += @($tier2 | ForEach-Object { Join-Path $out $_ } | Where-Object { Test-Path $_ }) }
foreach ($w in 'm56-v1', 'm56-v6', 'm56-v7', 'm56-v8', 'm56-e5', 'm56-e6') {
  $root = Join-Path 'D:\AI\CARLA-Funny-Moments.worktrees' $w
  if (Test-Path $root) {
    Get-ChildItem $root -Recurse -Directory -Force -Filter '__pycache__' -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -notmatch '\\\.venv' } | ForEach-Object { $targets += $_.FullName }
  }
}
$freed = 0
foreach ($t in $targets) {
  $files = Get-ChildItem $t -Recurse -File -Force
  $size = ($files | Measure-Object Length -Sum).Sum
  if ($t -notmatch '__pycache__') {
    $manifest = Join-Path $here ('manifest-' + (Split-Path $t -Leaf) + '.tsv')
    $files | ForEach-Object { "{0}`t{1}" -f $_.FullName.Substring($t.Length + 1), $_.Length } | Set-Content $manifest -Encoding UTF8
  }
  Remove-Item $t -Recurse -Force
  $freed += $size
  "{0,10:N0} MB  {1}" -f ($size / 1MB), $t
}
"Freed {0:N2} GB in {1} folders; manifests in {2}" -f ($freed / 1GB), $targets.Count, $here
