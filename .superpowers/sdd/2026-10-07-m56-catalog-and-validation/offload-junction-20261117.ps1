# 2026-11-17: D: still < 80 GB after the 34.9 GB move (sealed bundles hard-link their sources, so logical bytes overstate the
# space freed). Move dirs that code still reads to E:\m56-offload-20261116\<rel> and leave a directory JUNCTION at the old path,
# so every reader (tests, asel2-release, pair/eligibility) resolves unchanged. Per item: robocopy -> verify count+bytes -> delete
# -> mklink /J -> verify the junction lists the same file count. Log: outputs/m56_offload_20261117_junction.jsonl. Stops at D >= 82 GB.
param([string[]]$Rel)
$O = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'; $E = 'E:\m56-offload-20261116'; $Log = "$O\m56_offload_20261117_junction.jsonl"
foreach ($rel in $Rel) {
    if ((Get-PSDrive D).Free / 1GB -ge 82) { 'TARGET_REACHED'; break }
    $src = Join-Path $O $rel; $dst = Join-Path $E $rel
    $it = Get-Item $src -Force -EA SilentlyContinue
    if ($null -eq $it -or $it.LinkType) { "SKIP $rel"; continue }
    # robocopy follows inner symlinks (pytest_receipts has 184): the copy would not match the source, so keep such items on D
    if (@(gci $src -Recurse -Force -Attributes ReparsePoint -EA SilentlyContinue).Count) { "SKIP_REPARSE $rel"; continue }
    $f = @(gci $src -Recurse -Force -File); $n = $f.Count; $b = [int64]($f | Measure Length -Sum).Sum
    robocopy $src $dst /E /COPY:DT /R:2 /W:5 /NFL /NDL /NP /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { "FAIL robocopy $rel rc=$LASTEXITCODE"; exit 2 }
    $g = @(gci $dst -Recurse -Force -File); $gb = [int64]($g | Measure Length -Sum).Sum
    if ($g.Count -ne $n -or $gb -ne $b) { "FAIL verify $rel files $($g.Count)/$n bytes $gb/$b"; exit 3 }
    Remove-Item $src -Recurse -Force -Confirm:$false
    cmd /c mklink /J "$src" "$dst" | Out-Null
    $j = @(gci $src -Recurse -Force -File).Count
    if ($j -ne $n) { "FAIL junction $rel $j/$n"; exit 4 }
    @{ rel = $rel; files = $n; bytes = $b; e = $dst; junction = $true; utc = (Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Compress | Add-Content $Log -Encoding utf8
    "JUNCTION {0} {1:N2} GB D_free={2:N1}" -f $rel, ($b / 1GB), ((Get-PSDrive D).Free / 1GB)
}
"JUNCTION_END D_free={0:N1} GB" -f ((Get-PSDrive D).Free / 1GB)
