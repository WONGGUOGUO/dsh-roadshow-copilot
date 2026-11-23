param([string]$SessionDir = "")
$ErrorActionPreference = "Stop"

if (-not $SessionDir) {
    $roots = @((Join-Path $env:USERPROFILE "Documents\路演记录"), (Join-Path (Get-Location) ".roadshow"))
    $cands = foreach ($r in $roots) {
        Get-ChildItem $r -Directory -ErrorAction SilentlyContinue
    }
    $s = $cands | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $s) { throw "no session found (Documents\路演记录 or .roadshow)" }
    $SessionDir = $s.FullName
}

$statePath = Join-Path $SessionDir "state.json"
$stopFlag = Join-Path $SessionDir "stop.flag"
Set-Content -Path $stopFlag -Value "stop" -Encoding ASCII

$pids = @()
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
    $pids = @($state.frames_pid, $state.audio_pid) | Where-Object { $_ }
    if ($state.root) { $root = $state.root }
}

foreach ($p in $pids) {
    $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
    if ($proc) { $proc.WaitForExit(15000) | Out-Null }
}
foreach ($p in $pids) {
    $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
}

$Python = Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) { $Python = "python.exe" }

& $Python (Join-Path $root "scripts\finalize_wav.py") $SessionDir

$frames = @(Get-ChildItem (Join-Path $SessionDir "frames") -Filter *.jpg -ErrorAction SilentlyContinue)
$audio = @(Get-ChildItem (Join-Path $SessionDir "audio") -Filter *.wav -ErrorAction SilentlyContinue)
$mb = [math]::Round((($audio | Measure-Object Length -Sum).Sum) / 1MB, 1)

Write-Output "STOPPED"
Write-Output ("session: " + $SessionDir)
Write-Output ("frames: " + $frames.Count + "  audio files: " + $audio.Count + " (" + $mb + " MB)")
