# EYKO-117: Head 3 phone intake harness. One command per run; works on any phone with only adb + this repo + uv.
#
# Usage (from the repo root, PowerShell):
#   powershell -ExecutionPolicy Bypass -File docs\phone-kit\run-head3.ps1 -Serial <adb serial> -Scenario S1 -Run 1 -Clip C:\path\PXL_20261014_094359202.mp4
#   S1  one kit clip alone, app in front (-Videos 1, three runs per clip: -Run 1, 2, 3)
#   S2  queue of ten: add both kit clips 5 times (-Videos 10; delete them afterwards)
#   S3  copy time: the largest kit clip (-Videos 1); the copy time is measured by watching the file grow in the app's folder
#   S4  back-fill: NOT automated yet (waits for Rafique's SQL that marks one stage missing); the script says so and stops
# What it does: device sheet -> clears logcat -> starts watching (battery and temperature every 30 s, the copy of each new video) ->
# YOU add the clip(s) through the Video tab picker when it says so -> waits until every video is `ready` (or -TimeoutMin) -> saves the raw
# `logcat -d -s EykonVideo`, the job table result and the end battery -> runs src\benchmarks\head3_intake.py to append
# stage_times.csv and run_summary.csv in -Out. Never runs connectedDebugAndroidTest. Reads only the app's own folder and the battery.
# -ReplayLog <file> skips the phone completely and feeds a saved log to the parser (a test of the pipeline without a phone).
param(
    [string]$Serial = "",
    [Parameter(Mandatory = $true)][ValidateSet("S1", "S2", "S3", "S4")][string]$Scenario,
    [Parameter(Mandatory = $true)][string]$Run,
    [string]$Clip = "",
    [int]$Videos = 1,
    [string]$Commit = "",
    [string]$Out = "docs\results\head3",
    [int]$TimeoutMin = 30,
    [string]$Adb = "adb",
    [string]$ReplayLog = ""
)

$ErrorActionPreference = "Stop"
$Pkg = "com.eykon.memory"
if ($Scenario -eq "S4") {
    Write-Host "S4 (back-fill) is not automated yet: it needs the SQL that marks one stage missing for an old video (ask Rafique on EYKO-117)." -ForegroundColor Yellow
    exit 2
}

function Adb-Run([string[]]$ArgList) {
    if ($Serial) { & $Adb -s $Serial @ArgList } else { & $Adb @ArgList }
}

function Battery-Reading {
    $text = (Adb-Run @("shell", "dumpsys", "battery")) -join "`n"
    $level = [int]([regex]::Match($text, "level:\s*(\d+)").Groups[1].Value)
    $temp = [double]([regex]::Match($text, "temperature:\s*(\d+)").Groups[1].Value) / 10.0
    return [pscustomobject]@{ Level = $level; Temp = $temp }
}

$date = Get-Date -Format "yyyy-MM-dd"
$stampName = Get-Date -Format "HHmm"

if ($ReplayLog) {
    $phone = "replay"
    $raw = Join-Path $Out "raw\$date-$phone-$Scenario-run$Run"
    New-Item -ItemType Directory -Force $raw | Out-Null
    Copy-Item $ReplayLog (Join-Path $raw "eykonvideo-logcat.txt") -Force
    if (-not $Commit) { $Commit = "replay" }
    uv run python src\benchmarks\head3_intake.py parse --log (Join-Path $raw "eykonvideo-logcat.txt") --out $Out --phone $phone --commit $Commit --scenario $Scenario --run $Run
    exit $LASTEXITCODE
}

# ---- device sheet -------------------------------------------------------------------------------------------------------
$state = (Adb-Run @("get-state")) -join ""
if ($state.Trim() -ne "device") { throw "No phone in 'device' state (adb get-state said '$state'). Plug it in, accept the prompt, or pass -Serial." }
$model = ((Adb-Run @("shell", "getprop", "ro.product.model")) -join "").Trim()
$phone = ($model -replace "[^A-Za-z0-9]+", "_")
if (-not $Commit) {
    $Commit = ((git rev-parse --short HEAD) 2>$null) -join ""
    if (-not $Commit) { $Commit = "unknown" }
}
$raw = Join-Path $Out "raw\$date-$phone-$Scenario-run$Run-$stampName"
New-Item -ItemType Directory -Force $raw | Out-Null
$sheet = @()
$sheet += "model: $model"
$sheet += "manufacturer: " + ((Adb-Run @("shell", "getprop", "ro.product.manufacturer")) -join "").Trim()
$sheet += "soc: " + ((Adb-Run @("shell", "getprop", "ro.soc.model")) -join "").Trim()
$sheet += "android: " + ((Adb-Run @("shell", "getprop", "ro.build.version.release")) -join "").Trim()
$sheet += "commit (repo HEAD or -Commit; the installed APK may differ, check KIT-VERSION.txt): $Commit"
$sheet += "app version: " + ((Adb-Run @("shell", "dumpsys", "package", $Pkg)) | Select-String "versionName|lastUpdateTime" | ForEach-Object { $_.Line.Trim() }) -join "; "
$sheet += "--- dumpsys battery"
$sheet += Adb-Run @("shell", "dumpsys", "battery")
$sheet += "--- thermalservice (first lines; empty on phones without it)"
$sheet += (Adb-Run @("shell", "dumpsys", "thermalservice")) | Select-Object -First 25
$sheet += "--- df -h /data"
$sheet += Adb-Run @("shell", "df", "-h", "/data")
$sheet += "--- MemTotal / MemAvailable"
$sheet += (Adb-Run @("shell", "cat", "/proc/meminfo")) | Select-String "MemTotal|MemAvailable"
$sheet | Out-File -Encoding utf8 (Join-Path $raw "device-sheet.txt")

# ---- start --------------------------------------------------------------------------------------------------------------
Adb-Run @("logcat", "-G", "16M") | Out-Null
Adb-Run @("logcat", "-c") | Out-Null
$battery = Join-Path $raw "battery.csv"
"time,level_pct,temp_c" | Out-File -Encoding ascii $battery
$b0 = Battery-Reading
"$(Get-Date -Format s),$($b0.Level),$($b0.Temp)" | Out-File -Encoding ascii -Append $battery
$clipBytes = 0
if ($Clip -and (Test-Path $Clip)) { $clipBytes = (Get-Item $Clip).Length }

Write-Host ""
Write-Host ">>> $Scenario run $Run on $model. NOW add $Videos video(s) through the app's Video tab and leave the app in front." -ForegroundColor Green
Write-Host ">>> Battery $($b0.Level) %, $($b0.Temp) C. Timeout $TimeoutMin min." -ForegroundColor Green

$clock = [System.Diagnostics.Stopwatch]::StartNew()
$copy = @{}          # file name -> @{ first = ms; lastChange = ms; size = bytes }
$nextBattery = 30000
$ready = 0
while ($clock.Elapsed.TotalMinutes -lt $TimeoutMin) {
    $listing = (Adb-Run @("shell", "run-as $Pkg sh -c 'ls -l files/videos/*/* 2>/dev/null'")) -join "`n"
    foreach ($m in [regex]::Matches($listing, "(\d+)\s+\d{4}-\d\d-\d\d\s+\d\d:\d\d\s+(\S+)")) {
        $size = [long]$m.Groups[1].Value
        $name = $m.Groups[2].Value
        if (-not $name.Contains("/")) { continue }
        $now = $clock.ElapsedMilliseconds
        if (-not $copy.ContainsKey($name)) { $copy[$name] = @{ first = $now; lastChange = $now; size = $size } }
        elseif ($copy[$name].size -ne $size) { $copy[$name].lastChange = $now; $copy[$name].size = $size }
    }
    if ($clock.ElapsedMilliseconds -ge $nextBattery) {
        $b = Battery-Reading
        "$(Get-Date -Format s),$($b.Level),$($b.Temp)" | Out-File -Encoding ascii -Append $battery
        $nextBattery += 30000
        $log = (Adb-Run @("logcat", "-d", "-s", "EykonVideo")) -join "`n"
        $ready = ([regex]::Matches($log, "finish [0-9a-f]{32}: ready")).Count
        Write-Host ("  {0,5:N0} s  battery {1} %  {2} C  videos ready {3}/{4}" -f $clock.Elapsed.TotalSeconds, $b.Level, $b.Temp, $ready, $Videos)
        if ($ready -ge $Videos) { break }
    }
    Start-Sleep -Milliseconds 400
}
$timedOut = ($ready -lt $Videos)

# ---- end ----------------------------------------------------------------------------------------------------------------
$b1 = Battery-Reading
"$(Get-Date -Format s),$($b1.Level),$($b1.Temp)" | Out-File -Encoding ascii -Append $battery
$logFile = Join-Path $raw "eykonvideo-logcat.txt"
(Adb-Run @("logcat", "-d", "-v", "time", "-s", "EykonVideo")) | Out-File -Encoding utf8 $logFile
(Adb-Run @("shell", "dumpsys", "battery")) | Out-File -Encoding utf8 (Join-Path $raw "battery-end.txt")

# copy time: from the moment a video file first showed up to the last time its size changed, only files that reached the clip's size
$copyMs = @()
foreach ($name in $copy.Keys) {
    $c = $copy[$name]
    if ($clipBytes -gt 0 -and $c.size -ne $clipBytes) { continue }
    $copyMs += [int]($c.lastChange - $c.first)
}
$copyNote = "copy time = first sight of the file to its last size change, polled about every 0.5 s, so it is a bit low or high by that much; a file already complete at the first look counts as 0"
$notes = if ($timedOut) { "TIMED OUT after $TimeoutMin min with $ready of $Videos ready. $copyNote" } else { $copyNote }

$args2 = @("run", "python", "src\benchmarks\head3_intake.py", "parse", "--log", $logFile, "--out", $Out, "--phone", $model, "--commit", $Commit,
    "--scenario", $Scenario, "--run", $Run, "--battery", $battery, "--notes", $notes)
if ($copyMs.Count -gt 0) { $args2 += "--copy-ms"; $args2 += ($copyMs | ForEach-Object { "$_" }) }
& uv @args2
$code = $LASTEXITCODE
Write-Host "Raw files: $raw" -ForegroundColor Cyan
if ($timedOut) { Write-Host "Timed out: not every video reached ready." -ForegroundColor Red; exit 3 }
exit $code

