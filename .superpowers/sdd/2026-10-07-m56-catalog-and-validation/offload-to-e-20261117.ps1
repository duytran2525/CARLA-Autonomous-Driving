# 2026-11-17 (user: upload to Drive is ~0.25 MB/s, so move the rest to E: now, upload to Drive later from E:). For every item of
# outputs/m56_offload_20261116_plan.json + release run-2 elig/* still on D: robocopy to E:\m56-offload-20261116\<rel>, verify file
# count + bytes on E:, then delete from D. Log: outputs/m56_offload_20261117_E.jsonl.
param([string]$Plan = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_offload_20261116_plan.json')
$O = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'; $E = 'E:\m56-offload-20261116'; $Log = "$O\m56_offload_20261117_E.jsonl"
$items = @((Get-Content $Plan -Raw | ConvertFrom-Json).move | % { $_[0] })
$items += @(gci "$O\m56_asel2_release_20261115T054325Z\elig" -Directory -EA SilentlyContinue | % { "m56_asel2_release_20261115T054325Z\elig\$($_.Name)" })
foreach ($rel in $items) {
    $src = Join-Path $O $rel; $dst = Join-Path $E $rel
    if (-not (Test-Path $src)) { continue }
    $f = @(gci $src -Recurse -Force -File); $n = $f.Count; $b = [int64]($f | Measure Length -Sum).Sum
    robocopy $src $dst /E /COPY:DT /R:2 /W:5 /NFL /NDL /NP /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { "FAIL robocopy $rel rc=$LASTEXITCODE"; exit 2 }
    $g = @(gci $dst -Recurse -Force -File); $gb = [int64]($g | Measure Length -Sum).Sum
    if ($g.Count -ne $n -or $gb -ne $b) { "FAIL verify $rel files $($g.Count)/$n bytes $gb/$b"; exit 3 }
    Remove-Item $src -Recurse -Force -Confirm:$false
    @{ rel = $rel; files = $n; bytes = $b; e = $dst; utc = (Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress | Add-Content $Log -Encoding utf8
    "MOVED_E {0} {1:N2} GB D_free={2:N1}" -f $rel, ($b / 1GB), ((Get-PSDrive D).Free / 1GB)
}
"E_END D_free={0:N1} GB E_free={1:N1} GB" -f ((Get-PSDrive D).Free / 1GB), ((Get-PSDrive E).Free / 1GB)
