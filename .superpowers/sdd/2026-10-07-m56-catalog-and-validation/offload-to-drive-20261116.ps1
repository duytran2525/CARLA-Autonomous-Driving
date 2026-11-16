# 2026-11-16 (user: D: >= 80 GB free, move to Google Drive uncompressed). Moves the dirs listed by offload-plan-20261116.py
# plus the release run-2 'elig' subfolders to G:\My Drive\m56-offload-20261116\<same relative path>, in ~6 GB batches.
# Per item: robocopy -> verify file count + bytes on G: -> delete from D. Before each batch waits until the DriveFS content cache
# (on C:) is < 3 GB and C: free >= 15 GB, so Drive uploads cannot fill C: (asel2-cguard stops M56 below 10 GB).
# Manifest (append per item): outputs/m56_offload_20261116_MANIFEST.jsonl. Restore: robocopy G:\My Drive\m56-offload-20261116\<rel> back.
param([string]$Plan)
$O = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'; $G = 'G:\My Drive\m56-offload-20261116'
$Man = "$O\m56_offload_20261116_MANIFEST.jsonl"; $Cache = "$env:LOCALAPPDATA\Google\DriveFS"
function cacheGB { [math]::Round(((gci $Cache -Recurse -Force -File -EA SilentlyContinue | ? { $_.FullName -match 'content_cache' } | Measure Length -Sum).Sum) / 1GB, 2) }
function cFree { [math]::Round((Get-PSDrive C).Free / 1GB, 1) }
function waitRoom { while ((cacheGB) -gt 3 -or (cFree) -lt 15) { "WAIT cache={0} GB C={1} GB {2:u}" -f (cacheGB), (cFree), (Get-Date).ToUniversalTime(); Start-Sleep 120 } }
$items = @((Get-Content $Plan -Raw | ConvertFrom-Json).move | % { $_[0] })
$items += @(gci "$O\m56_asel2_release_20261115T054325Z\elig" -Directory | % { "m56_asel2_release_20261115T054325Z\elig\$($_.Name)" })
$batch = 0
foreach ($rel in $items) {
    $src = Join-Path $O $rel; $dst = Join-Path $G $rel
    if (-not (Test-Path $src)) { continue }
    $files = @(gci $src -Recurse -Force -File); $n = $files.Count; $b = ($files | Measure Length -Sum).Sum; if ($null -eq $b) { $b = 0 }
    if ($batch -eq 0 -or $batch + $b -gt 6GB) { waitRoom; $batch = 0 }
    robocopy $src $dst /E /COPY:DT /R:3 /W:10 /NFL /NDL /NP /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { "FAIL robocopy $rel rc=$LASTEXITCODE"; exit 2 }
    $g = @(gci $dst -Recurse -Force -File); $gb = ($g | Measure Length -Sum).Sum; if ($null -eq $gb) { $gb = 0 }
    if ($g.Count -ne $n -or $gb -ne $b) { "FAIL verify $rel files $($g.Count)/$n bytes $gb/$b"; exit 3 }
    Remove-Item $src -Recurse -Force -Confirm:$false
    @{ rel = $rel; files = $n; bytes = $b; drive = $dst; utc = (Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress | Add-Content $Man -Encoding utf8
    $batch += $b
    "MOVED {0} {1:N2} GB D_free={2:N1}" -f $rel, ($b / 1GB), ((Get-PSDrive D).Free / 1GB)
}
waitRoom
"OFFLOAD_END D_free={0:N1} GB C_free={1} cache={2}" -f ((Get-PSDrive D).Free / 1GB), (cFree), (cacheGB)
