# EYKO-94: run the sqlite-vec storage test on this phone and save the raw log.
# Each command is printed before it runs, so a screen recording shows what was run.
# Usage (from C:\eykon-kit):  powershell -ExecutionPolicy Bypass -File .\run-eyko94.ps1 [-Tag -run2]
param([string]$Tag = "")

$date = Get-Date -Format "yyyy-MM-dd"
$out = "infinix-$date-logcat$Tag.txt"

function Run([string]$cmd) {
    Write-Host ""
    Write-Host "PS> $cmd" -ForegroundColor Yellow
    Invoke-Expression $cmd
}

Run "adb devices"
Run "adb logcat -G 16M"
Run "adb logcat -c"
Run "adb shell am instrument -w -e class com.eykon.memory.spike.VectorStorageSpikeTest com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner"
Run "adb logcat -d -s EYKO31 | Out-File -Encoding utf8 $out"
Run "(Get-Item $out).Length"
Run "Select-String -Path $out -Pattern 'device|vec0|load_extension' | ForEach-Object { `$_.Line }"
Write-Host ""
Write-Host "Saved: $out" -ForegroundColor Green
