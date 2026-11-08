# 2026-11-08: free disk space on D: WITHOUT deleting anything - NTFS (WOF LZX) transparent compression of the finished M56
# output directories. Bytes, paths and sha256 stay identical (every SourceRef still verifies); undo with
#   compact.exe /U /S:<dir> /EXE /I /Q
# Skips the running full-suite basetemp (m56-full-suite-10b-20261108) and anything outside m56-v1\outputs.
$out = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'
$skip = @("$out\m56_offline_v1\pytest_receipts\m56-full-suite-10b-20261108")
$dirs = @(Get-ChildItem $out -Directory | Where-Object Name -ne 'm56_offline_v1')
$dirs += Get-ChildItem "$out\m56_offline_v1" -Directory | Where-Object Name -ne 'pytest_receipts'
$dirs += Get-ChildItem "$out\m56_offline_v1\pytest_receipts" -Directory | Where-Object { $skip -notcontains $_.FullName }
$log = "$out\m56_compact_20261108.log"
"start $(Get-Date -Format o) dirs=$($dirs.Count) free=$((Get-PSDrive D).Free)" | Add-Content $log
foreach ($d in $dirs) {
  $r = compact.exe /C /S:"$($d.FullName)" /EXE:LZX /I /Q | Select-Object -Last 2
  "$($d.Name) | $($r -join ' ')" | Add-Content $log
}
# loose files directly under outputs
compact.exe /C "$out\*" /EXE:LZX /I /Q | Select-Object -Last 2 | Add-Content $log
"end $(Get-Date -Format o) free=$((Get-PSDrive D).Free)" | Add-Content $log
