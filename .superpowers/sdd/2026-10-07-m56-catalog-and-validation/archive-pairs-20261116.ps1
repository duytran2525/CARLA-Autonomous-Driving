# 2026-11-16: free D: by archiving offline pair-evaluation dirs (m56_v6_pair_*) that no doc/script/output references.
# They are re-derivable (offline, no server, no P5) from the A/B dirs, which stay. Each dir -> one tar.zst on E:, verified
# (entry count == source file count), manifest with sha256/md5 of the archive. Upload/delete are separate steps.
# usage: pwsh archive-pairs-20261116.ps1 <csv with columns N,ref>
param([string]$Csv)
$o = 'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'; $dst = 'E:\m56-archive\pairs'
New-Item -ItemType Directory -Force $dst | Out-Null
$rows = Import-Csv $Csv | ? { $_.ref -eq 'False' -and $_.N -notlike '*20261116*' }
$man = foreach ($r in $rows) {
    $src = Join-Path $o $r.N; $arc = Join-Path $dst "$($r.N).tar.zst"
    $files = gci $src -Recurse -File; $n = $files.Count; $bytes = ($files | Measure Length -Sum).Sum
    tar --zstd -cf $arc -C $o $r.N; if ($LASTEXITCODE) { throw "tar failed $($r.N)" }
    $entries = (tar -tf $arc | ? { $_ -notmatch '/$' }).Count
    if ($entries -ne $n) { throw "count mismatch $($r.N): $entries vs $n" }
    [pscustomobject]@{ dir = $r.N; files = $n; src_bytes = $bytes; archive = (Split-Path $arc -Leaf); archive_bytes = (gi $arc).Length
        sha256 = (Get-FileHash $arc SHA256).Hash.ToLower(); md5 = (Get-FileHash $arc MD5).Hash.ToLower() }
}
$man | ConvertTo-Json | Set-Content "$dst\MANIFEST.json" -Encoding utf8
"ARCHIVED {0} dirs, src {1:N2} GB -> {2:N2} GB" -f $man.Count, (($man | Measure src_bytes -Sum).Sum / 1GB), (($man | Measure archive_bytes -Sum).Sum / 1GB)
