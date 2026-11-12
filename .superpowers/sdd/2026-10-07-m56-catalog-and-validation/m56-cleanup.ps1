<#
M56 cleanup (2026-11-12, user request "script dọn rác và dữ liệu không cần tới nữa").
Never deletes by itself: -Apply MOVES the candidates into a trash folder on the same drive (instant rename) and writes
manifest.json there; -Restore puts them back; only -Purge (run by the user) deletes a trash folder for good.
Candidates (everything else in outputs/ is run evidence for pairs, the release or the audit and is never touched):
  1. outputs/m56_v14_flake_diag/runs and prev_runs_partial: copies made by the v14 flake diagnosis (done 10/11, result in
     the batch log); its logs, fixed_root.py and v14_regression.txt stay.
  2. %TEMP%\claude\<project>\<entry> not written for 7 days: Claude Code task outputs / scratch of old sessions.
  3. My helper files in outputs/: m56_size_scan_*, m56_commit_msg_*.
usage (PowerShell):
  .\m56-cleanup.ps1                 # dry run: list candidates and sizes
  .\m56-cleanup.ps1 -Apply          # move them to trash (refused while CARLA / an M56 job runs)
  .\m56-cleanup.ps1 -Restore <trash folder>
  .\m56-cleanup.ps1 -Purge <trash folder>   # permanent delete of one trash folder
#>
param([switch]$Apply, [string]$Restore, [string]$Purge)
$ErrorActionPreference = 'Stop'
$O = (Resolve-Path "$PSScriptRoot\..\..\..\outputs").Path
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')

if ($Purge) {
    if ((Split-Path $Purge -Leaf) -notlike 'm56_trash_*' -or -not (Test-Path "$Purge\manifest.json")) { throw "not an m56 trash folder: $Purge" }
    Remove-Item -LiteralPath $Purge -Recurse -Force; "PURGED $Purge"; return
}
if ($Restore) {
    $m = Get-Content "$Restore\manifest.json" -Raw | ConvertFrom-Json
    foreach ($r in $m) { if (Test-Path -LiteralPath $r.src) { "SKIP exists: $($r.src)" } else { New-Item -ItemType Directory -Force (Split-Path $r.src) | Out-Null; Move-Item -LiteralPath $r.dst -Destination $r.src; "RESTORED $($r.src)" } }
    return
}

function SizeMB($p) {
    if (Test-Path -LiteralPath $p -PathType Leaf) { return [math]::Round((Get-Item -LiteralPath $p).Length / 1MB, 1) }
    $n = 0; foreach ($f in [IO.Directory]::EnumerateFiles($p, '*', 'AllDirectories')) { $n += ([IO.FileInfo]$f).Length }
    [math]::Round($n / 1MB, 1)
}
$c = [System.Collections.Generic.List[object]]::new()
foreach ($d in 'runs', 'prev_runs_partial') {
    $p = "$O\m56_v14_flake_diag\$d"; if (Test-Path $p) { $c.Add([pscustomobject]@{src = $p; reason = 'v14 flake diagnosis copies (done 10/11)' }) }
}
$cut = (Get-Date).AddDays(-7)
$session = if ($env:CLAUDE_SESSION_ID) { $env:CLAUDE_SESSION_ID } else { '' }
if (Test-Path "$env:TEMP\claude") {
    Get-ChildItem "$env:TEMP\claude" -Directory | ForEach-Object { Get-ChildItem $_.FullName -Force } |
        Where-Object { $_.LastWriteTime -lt $cut -and ($session -eq '' -or $_.Name -ne $session) } |
        ForEach-Object { $c.Add([pscustomobject]@{src = $_.FullName; reason = 'Claude Code temp, untouched 7+ days' }) }
}
Get-ChildItem $O -File | Where-Object { $_.Name -like 'm56_size_scan_*' -or $_.Name -like 'm56_commit_msg_*' } |
    ForEach-Object { $c.Add([pscustomobject]@{src = $_.FullName; reason = 'helper file' }) }

foreach ($r in $c) { $r | Add-Member mb (SizeMB $r.src) }
$c | Sort-Object mb -Descending | Format-Table mb, reason, src -AutoSize | Out-String -Width 250
"TOTAL {0} MB in {1} items" -f [math]::Round(($c | Measure-Object mb -Sum).Sum, 1), $c.Count
if (-not $Apply) { 'DRY RUN (nothing moved). Use -Apply to move to trash.'; return }

$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'CarlaUE4*' -or $_.CommandLine -match 'native-[\w-]+\.py|run-asel2-|run-f0[1-3]-|pytest' }
if ($busy) { throw "REFUSED: CARLA or an M56 job is running (pid $($busy.ProcessId -join ','))" }
$moved = @{}
foreach ($r in $c) {
    $drive = [IO.Path]::GetPathRoot($r.src)
    $trash = if ($drive -eq [IO.Path]::GetPathRoot($O)) { "$O\m56_trash_$stamp" } else { "$env:TEMP\..\m56_trash_$stamp" }
    $trash = [IO.Path]::GetFullPath($trash)
    $dst = Join-Path $trash ($r.src.Substring($drive.Length))
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Move-Item -LiteralPath $r.src -Destination $dst
    if (-not $moved[$trash]) { $moved[$trash] = [System.Collections.Generic.List[object]]::new() }
    $moved[$trash].Add([pscustomobject]@{src = $r.src; dst = $dst; mb = $r.mb; reason = $r.reason })
}
foreach ($t in $moved.Keys) {
    $moved[$t] | ConvertTo-Json -Depth 3 | Set-Content "$t\manifest.json" -Encoding utf8
    "MOVED $($moved[$t].Count) items -> $t"
    "  restore: .\m56-cleanup.ps1 -Restore '$t'"
    "  free the space for good: .\m56-cleanup.ps1 -Purge '$t'"
}
