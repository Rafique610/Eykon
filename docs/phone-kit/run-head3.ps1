# EYKO-117: Head 3 phone intake harness. One command per run; works on any phone with only adb + this repo + uv.
#
# Usage (from the repo root, PowerShell):
#   powershell -ExecutionPolicy Bypass -File docs\phone-kit\run-head3.ps1 -Serial <adb serial> -Scenario S1 -Run 1 -Clip C:\path\PXL_20261014_094359202.mp4
#   S1  one kit clip alone, app in front (-Videos 1, three runs per clip: -Run 1, 2, 3)
#   S2  queue of ten (-Videos 10): the script makes byte-different copies of the two kit clips on the phone (the app refuses identical bytes since
#       EYKO-71), 5 per clip, rescans them so the picker lists them, and tells you which 10 files to add. Delete them from the phone afterwards.
#   S3  copy time: the largest kit clip (-Videos 1). Taken from the app's `copy` log line when the build has it (EYKO-71), else by watching the file grow
#   S4  back-fill: -Scenario S4 [-VideoId <32 hex>] [-BackfillStage latest]. Force-stops the app, marks ONE finished video's saved stage as
#       <BackfillStage> in memories.db (WAL checkpointed first), puts the database back, opens the app, and records which stages run again.
#       With `latest` only `finish` should rerun (clean control); `link` reruns latest and finish.
# What S1-S3 do: device sheet -> clears logcat -> notes the files already in the app's video folder -> starts watching (every 5 s: is every video
# ready?; every 30 s: battery and temperature; the copy of each NEW video) -> YOU add the clip(s) through the Video tab picker when it says so ->
# waits until every video is `ready` (or -TimeoutMin) -> reads the battery at once -> saves the raw `logcat -d -s EykonVideo` -> runs
# src\benchmarks\head3_intake.py to append stage_times.csv and run_summary.csv in -Out.
# Never runs connectedDebugAndroidTest. Reads only the app's own folder and the battery.
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
    [string]$ReplayLog = "",
    [string]$VideoId = "",
    [string]$BackfillStage = "latest",
    # S2: the two kit clips as they sit on the phone; byte-different copies of them are made (the app refuses identical bytes since EYKO-71)
    [string]$SourceClips = "PXL_20261014_094359202.mp4,PXL_20261014_094903187.mp4",
    [string]$PhoneFolder = "/sdcard/Movies"
)

$ErrorActionPreference = "Stop"
$Pkg = "com.eykon.memory"

function Adb-Run([string[]]$ArgList) {
    if ($Serial) { & $Adb -s $Serial @ArgList } else { & $Adb @ArgList }
}

function Battery-Reading {
    $text = (Adb-Run @("shell", "dumpsys", "battery")) -join "`n"
    $level = [int]([regex]::Match($text, "level:\s*(\d+)").Groups[1].Value)
    $temp = [double]([regex]::Match($text, "temperature:\s*(\d+)").Groups[1].Value) / 10.0
    # charging or not: battery_used_pct means nothing while the phone charges (EYKO-117 review, 12 Nov)
    $plugged = "none"
    foreach ($kind in @(@("AC", "AC powered"), @("USB", "USB powered"), @("Wireless", "Wireless powered"))) {
        if ($text -match ($kind[1] + ":\s*true")) { $plugged = $kind[0]; break }
    }
    return [pscustomobject]@{ Level = $level; Temp = $temp; Plugged = $plugged }
}

# the files in the app's video folder as "path -> size"; $null when run-as does not work (not a debug build, or the app is not installed)
function Video-Files {
    $listing = (Adb-Run @("shell", "run-as $Pkg sh -c 'ls -l files/videos/*/* 2>&1'")) -join "`n"
    if ($listing -match "run-as:|not debuggable|Unknown package|Permission denied") { return $null }
    $found = @{}
    foreach ($m in [regex]::Matches($listing, "(\d+)\s+\d{4}-\d\d-\d\d\s+\d\d:\d\d\s+(\S+)")) {
        if ($m.Groups[2].Value.Contains("/")) { $found[$m.Groups[2].Value] = [long]$m.Groups[1].Value }
    }
    return $found
}

# S2: the app refuses a video whose bytes it already has (EYKO-71), so adding the same two clips five times fails. Make byte-different copies:
# copy N of a clip is the clip plus N empty "free" atoms (8 bytes each: 00 00 00 08 "free"); players and MediaStore read them as the same video.
# The originals are variant 0. Result: 5 distinct files per clip = 10 videos.
function Prepare-S2Files {
    $atom = Join-Path ([System.IO.Path]::GetTempPath()) "free-atom.bin"
    [System.IO.File]::WriteAllBytes($atom, [byte[]](0, 0, 0, 8, 102, 114, 101, 101))
    Adb-Run @("push", $atom, "/data/local/tmp/free-atom.bin") | Out-Null
    $names = @()
    foreach ($clipName in ($SourceClips -split ",")) {
        $clipName = $clipName.Trim()
        $names += $clipName
        $base = [System.IO.Path]::GetFileNameWithoutExtension($clipName)
        foreach ($n in 1..4) {
            $copyName = "$base-s2-$n.mp4"
            Adb-Run @("shell", "cp", "$PhoneFolder/$clipName", "$PhoneFolder/$copyName") | Out-Null
            foreach ($i in 1..$n) { Adb-Run @("shell", "cat /data/local/tmp/free-atom.bin >> $PhoneFolder/$copyName") | Out-Null }
            $names += $copyName
        }
    }
    foreach ($name in $names) {
        Adb-Run @("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", "file://$PhoneFolder/$name") | Out-Null
    }
    Adb-Run @("shell", "rm", "-f", "/data/local/tmp/free-atom.bin") | Out-Null
    return $names
}

function Pull-File([string]$Remote, [string]$Local) {
    $serialPart = if ($Serial) { "-s $Serial " } else { "" }
    $line = "$Adb $serialPart" + "exec-out run-as $Pkg cat $Remote > `"$Local`""
    cmd /c $line
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
$sheet += "app version: " + (((Adb-Run @("shell", "dumpsys", "package", $Pkg)) | Select-String "versionName|lastUpdateTime" | ForEach-Object { $_.Line.Trim() }) -join "; ")
$sheet += "--- dumpsys battery"
$sheet += Adb-Run @("shell", "dumpsys", "battery")
$sheet += "--- thermalservice (first lines; empty on phones without it)"
$sheet += (Adb-Run @("shell", "dumpsys", "thermalservice")) | Select-Object -First 25
$sheet += "--- df -h /data"
$sheet += Adb-Run @("shell", "df", "-h", "/data")
$sheet += "--- MemTotal / MemAvailable"
$sheet += (Adb-Run @("shell", "cat", "/proc/meminfo")) | Select-String "MemTotal|MemAvailable"
$sheet | Out-File -Encoding utf8 (Join-Path $raw "device-sheet.txt")

$battery = Join-Path $raw "battery.csv"
"time,level_pct,temp_c,plugged" | Out-File -Encoding ascii $battery

# ---- S4: back-fill ------------------------------------------------------------------------------------------------------
if ($Scenario -eq "S4") {
    $dbDir = Join-Path $raw "db"
    New-Item -ItemType Directory -Force $dbDir | Out-Null
    Adb-Run @("shell", "am", "force-stop", $Pkg) | Out-Null
    foreach ($n in "memories.db", "memories.db-wal", "memories.db-shm") { Pull-File "databases/$n" (Join-Path $dbDir $n) }
    # S4 replaces the live database, so keep all three files as they were (the -wal and -shm files can hold recent rows)
    foreach ($n in "memories.db", "memories.db-wal", "memories.db-shm") {
        $src = Join-Path $dbDir $n
        if (Test-Path $src) { Copy-Item $src (Join-Path $raw "$n.before-backfill") -Force }
    }
    $pyArgs = @("run", "python", "src\benchmarks\head3_intake.py", "backfill", "--db", (Join-Path $dbDir "memories.db"), "--stage", $BackfillStage)
    if ($VideoId) { $pyArgs += @("--video-id", $VideoId) }
    $changed = (& uv @pyArgs) -join "`n"
    Write-Host $changed
    if ($LASTEXITCODE -ne 0) { throw "backfill step failed: $changed" }
    $picked = [regex]::Match($changed, "video ([0-9a-f]{32})").Groups[1].Value
    Adb-Run @("push", (Join-Path $dbDir "memories.db"), "/data/local/tmp/memories.db") | Out-Null
    Adb-Run @("shell", "run-as $Pkg sh -c 'rm -f databases/memories.db-wal databases/memories.db-shm; cp /data/local/tmp/memories.db databases/memories.db; chmod 660 databases/memories.db'") | Out-Null
    Adb-Run @("shell", "rm", "/data/local/tmp/memories.db") | Out-Null
    Adb-Run @("logcat", "-G", "16M") | Out-Null
    Adb-Run @("logcat", "-c") | Out-Null
    $b0 = Battery-Reading
    "$(Get-Date -Format s),$($b0.Level),$($b0.Temp),$($b0.Plugged)" | Out-File -Encoding ascii -Append $battery
    Adb-Run @("shell", "monkey", "-p", $Pkg, "-c", "android.intent.category.LAUNCHER", "1") | Out-Null
    Write-Host ">>> S4: app opened; waiting for video $picked to finish again (timeout $TimeoutMin min)." -ForegroundColor Green
    $clock4 = [System.Diagnostics.Stopwatch]::StartNew()
    $done = $false
    while ($clock4.Elapsed.TotalMinutes -lt $TimeoutMin) {
        $log = (Adb-Run @("logcat", "-d", "-s", "EykonVideo")) -join "`n"
        if ($log -match "finish $picked") { $done = $true; break }
        Start-Sleep -Seconds 3
    }
    $b1 = Battery-Reading
    "$(Get-Date -Format s),$($b1.Level),$($b1.Temp),$($b1.Plugged)" | Out-File -Encoding ascii -Append $battery
    $logFile = Join-Path $raw "eykonvideo-logcat.txt"
    (Adb-Run @("logcat", "-d", "-v", "time", "-s", "EykonVideo")) | Out-File -Encoding utf8 $logFile
    $stagesRun = [regex]::Matches((Get-Content $logFile -Raw), "EykonVideo\s*(?:\(\s*\d+\))?\s*:\s*(\w+) $picked") | ForEach-Object { $_.Groups[1].Value }
    Write-Host ("Stages that ran again for {0} (stage set to '{1}'): {2}" -f $picked, $BackfillStage, ($stagesRun -join ", ")) -ForegroundColor Cyan
    $notes = "back-fill: saved stage set to '$BackfillStage' for $picked; stages that ran again: $($stagesRun -join ' ')"
    uv run python src\benchmarks\head3_intake.py parse --log $logFile --out $Out --phone $model --commit $Commit --scenario S4 --run $Run --battery $battery --notes $notes
    if (-not $done) { Write-Host "Timed out: the video did not reach ready again." -ForegroundColor Red; exit 3 }
    exit 0
}

# ---- S1-S3: start -------------------------------------------------------------------------------------------------------
Adb-Run @("logcat", "-G", "16M") | Out-Null
Adb-Run @("logcat", "-c") | Out-Null
$b0 = Battery-Reading
"$(Get-Date -Format s),$($b0.Level),$($b0.Temp),$($b0.Plugged)" | Out-File -Encoding ascii -Append $battery
$clipBytes = 0
if ($Clip -and (Test-Path $Clip)) { $clipBytes = (Get-Item $Clip).Length }

# files already in the app's folder do not count as new copies (an earlier copy of the same clip would otherwise read as a copy that took 0 ms)
$existing = Video-Files
$runAsOk = ($null -ne $existing)
if (-not $runAsOk) {
    Write-Host "WARNING: run-as does not work on this phone (not a debug build?). Copy time by file growth is not available; it will be blank unless the build logs a 'copy' line." -ForegroundColor Yellow
    $existing = @{}
}

$s2Names = @()
if ($Scenario -eq "S2") {
    $s2Names = Prepare-S2Files
    Write-Host ">>> S2: made byte-different copies on the phone. Add ALL of these $($s2Names.Count) files, one after another:" -ForegroundColor Green
    $s2Names | ForEach-Object { Write-Host "      $_" }
    if ($Videos -ne $s2Names.Count) { Write-Host "WARNING: -Videos is $Videos but $($s2Names.Count) files were made; use -Videos $($s2Names.Count)." -ForegroundColor Yellow }
}

Write-Host ""
Write-Host ">>> $Scenario run $Run on $model. NOW add $Videos video(s) through the app's Video tab and leave the app in front." -ForegroundColor Green
if ($b0.Plugged -ne "none") { Write-Host ">>> The phone is charging ($($b0.Plugged)): battery_used_pct will not be battery use. Unplug the charger if you want that figure." -ForegroundColor Yellow }
Write-Host ">>> Battery $($b0.Level) %, $($b0.Temp) C. $($existing.Count) file(s) already in the app's video folder are ignored. Timeout $TimeoutMin min." -ForegroundColor Green

$clock = [System.Diagnostics.Stopwatch]::StartNew()
$copy = @{}          # file path -> @{ first = ms; lastChange = ms; size = bytes }
$nextBattery = 30000
$nextReady = 0
$ready = 0
while ($clock.Elapsed.TotalMinutes -lt $TimeoutMin) {
    if ($runAsOk) {
        $files = Video-Files
        if ($null -ne $files) {
            foreach ($name in $files.Keys) {
                if ($existing.ContainsKey($name)) { continue }
                $size = $files[$name]
                $now = $clock.ElapsedMilliseconds
                if (-not $copy.ContainsKey($name)) { $copy[$name] = @{ first = $now; lastChange = $now; size = $size } }
                elseif ($copy[$name].size -ne $size) { $copy[$name].lastChange = $now; $copy[$name].size = $size }
            }
        }
    }
    if ($clock.ElapsedMilliseconds -ge $nextReady) {
        $log = (Adb-Run @("logcat", "-d", "-s", "EykonVideo")) -join "`n"
        $ready = ([regex]::Matches($log, "finish [0-9a-f]{32}: ready")).Count
        $nextReady = $clock.ElapsedMilliseconds + 5000
        if ($ready -ge $Videos) { break }
    }
    if ($clock.ElapsedMilliseconds -ge $nextBattery) {
        $b = Battery-Reading
        "$(Get-Date -Format s),$($b.Level),$($b.Temp),$($b.Plugged)" | Out-File -Encoding ascii -Append $battery
        $nextBattery += 30000
        Write-Host ("  {0,5:N0} s  battery {1} %  {2} C  videos ready {3}/{4}" -f $clock.Elapsed.TotalSeconds, $b.Level, $b.Temp, $ready, $Videos)
    }
    Start-Sleep -Milliseconds 400
}
$timedOut = ($ready -lt $Videos)

# ---- end: battery first, at once ----------------------------------------------------------------------------------------
$b1 = Battery-Reading
"$(Get-Date -Format s),$($b1.Level),$($b1.Temp),$($b1.Plugged)" | Out-File -Encoding ascii -Append $battery
$logFile = Join-Path $raw "eykonvideo-logcat.txt"
(Adb-Run @("logcat", "-d", "-v", "time", "-s", "EykonVideo")) | Out-File -Encoding utf8 $logFile
(Adb-Run @("shell", "dumpsys", "battery")) | Out-File -Encoding utf8 (Join-Path $raw "battery-end.txt")

# copy time by file growth: from the first sight of a NEW file to the last change of its size; only files that reached the clip's size
$copyMs = @()
foreach ($name in $copy.Keys) {
    $c = $copy[$name]
    if ($clipBytes -gt 0 -and $c.size -ne $clipBytes) { continue }
    $copyMs += [int]($c.lastChange - $c.first)
}
$copyNote = "file-growth copy time (used only when the log has no copy line): first sight of a new file to its last size change, polled about every 0.5 s"
$notes = if ($timedOut) { "TIMED OUT after $TimeoutMin min with $ready of $Videos ready. $copyNote" } else { $copyNote }
if (-not $runAsOk) { $notes += " run-as did not work on this phone." }

$args2 = @("run", "python", "src\benchmarks\head3_intake.py", "parse", "--log", $logFile, "--out", $Out, "--phone", $model, "--commit", $Commit,
    "--scenario", $Scenario, "--run", $Run, "--battery", $battery, "--notes", $notes)
if ($copyMs.Count -gt 0) { $args2 += "--copy-ms"; $args2 += ($copyMs | ForEach-Object { "$_" }) }
& uv @args2
$code = $LASTEXITCODE
Write-Host "Raw files: $raw" -ForegroundColor Cyan
if ($timedOut) { Write-Host "Timed out: not every video reached ready." -ForegroundColor Red; exit 3 }
exit $code
