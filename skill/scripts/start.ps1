param(
    [string]$SessionDir = "",
    [string]$Keywords = "",
    [double]$Interval = 6,
    [double]$SegmentMinutes = 10,
    [double]$MaxHours = 6
)
$ErrorActionPreference = "Stop"
$Scripts = Split-Path -Parent $PSCommandPath
$Root = Split-Path -Parent $Scripts
$Python = Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $Python)) { $Python = "python.exe" }

if (-not $SessionDir) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $preferred = Join-Path (Join-Path $env:USERPROFILE "Documents\路演记录") $stamp
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $preferred) -ErrorAction Stop | Out-Null
        New-Item -ItemType Directory -Force -Path $preferred -ErrorAction Stop | Out-Null
        $SessionDir = $preferred
    } catch {
        $SessionDir = Join-Path (Join-Path (Get-Location) ".roadshow") $stamp
    }
}
New-Item -ItemType Directory -Force -Path $SessionDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $SessionDir "audio") | Out-Null

$stopFlag = Join-Path $SessionDir "stop.flag"
if (Test-Path $stopFlag) { Remove-Item $stopFlag -Force }

$framePy = Join-Path $Scripts "capture_frames.py"
$audioPy = Join-Path $Scripts "record_audio.py"
$audioDir = Join-Path $SessionDir "audio"

$env:PYTHONPATH = (Join-Path $Root "vendor")
$frameArg = '"{0}" "{1}" "{2}" {3} {4}' -f $framePy, $SessionDir, $Keywords, $Interval, ($MaxHours * 3600)
$audioArg = '"{0}" "{1}" {2}' -f $audioPy, $audioDir, ($SegmentMinutes * 60)

$frames = Start-Process -FilePath $Python -ArgumentList $frameArg -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $SessionDir "frames.log") `
    -RedirectStandardError (Join-Path $SessionDir "frames.err")
$audio = Start-Process -FilePath $Python -ArgumentList $audioArg -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $SessionDir "audio.log") `
    -RedirectStandardError (Join-Path $SessionDir "audio.err")

$state = [ordered]@{
    session    = $SessionDir
    frames_pid = $frames.Id
    audio_pid  = $audio.Id
    started    = (Get-Date).ToString("s")
    keywords   = $Keywords
    root       = $Root
}
$state | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $SessionDir "state.json")

Write-Output "RECORDING"
Write-Output ("session: " + $SessionDir)
Write-Output ("frames_pid: " + $frames.Id + "  audio_pid: " + $audio.Id)
