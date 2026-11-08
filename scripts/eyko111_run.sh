#!/usr/bin/env bash
# EYKO-111: run one condition on a phone (PHONE=a32 default, or PHONE=pixel9proxl SERIAL=...), unplugged, from a 60 s timer on the phone (EYKO-95 protocol).
#   scripts/eyko111_run.sh start <cool|hot|lowbat>   cable in: writes the "before" sheet, sets the timer
#   (pull the cable and turn flight mode on within 60 s; wait for the run to finish; plug back in)
#   scripts/eyko111_run.sh pull  <cool|hot|lowbat>   cable in again: "after" sheet, raw logcat, CSV, CPU log
#   scripts/eyko111_run.sh hold                      background-kill test (MAPPED_NATIVE, 3 tables at 100k, 300 s)
set -euo pipefail
export MSYS_NO_PATHCONV=1
PHONE=${PHONE:-a32}; SERIAL=${SERIAL:-RF8T20H8G5W}
ADB="/c/Users/rafique_/AppData/Local/Android/Sdk/platform-tools/adb.exe -s $SERIAL"
OUT="docs/results/vectors/proof"
CSV_DIR="docs/results/vectors/offheap"
DAY=$(date +%Y-%m-%d)
COMMIT=$(git rev-parse --short HEAD)
RUNNER="com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner"
CLS="com.eykon.memory.video.OffHeapVectorTest"
step=$1; cond=${2:-hold}
base="$OUT/$PHONE-$DAY-eyko111-$cond"

sheet() {  # $1 = label
  { echo "# $1: $(date '+%Y-%m-%d %H:%M:%S %z')"
    $ADB shell dumpsys battery | grep -E 'AC powered|USB powered|level|temperature'
    $ADB shell df -h /data/user/0 | tail -1; } >> "$base-device.txt"
}

case $step in
start)
  echo "# $PHONE ($SERIAL), commit $COMMIT, EYKO-111 condition: $cond" > "$base-device.txt"
  sheet "before (cable in, timer set)"
  $ADB logcat -G 16M; $ADB logcat -c
  $ADB shell "nohup sh -c 'sleep 60; \
    (while true; do echo \$(date +%T) \$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq | tr \"\\n\" \" \"); sleep 5; done) > /data/local/tmp/eyko111-$cond-cpufreq.txt 2>&1 & F=\$!; \
    am instrument -w -e class $CLS#speedAndAnswers -e modes HEAP_F32,MAPPED_NATIVE -e sizes 20k,50k,100k -e runs 5 -e commit $COMMIT $RUNNER \
      > /data/local/tmp/eyko111-$cond.txt 2>&1; kill \$F' > /dev/null 2>&1 &"
  echo "Timer set at $(date +%T). Pull the cable and turn flight mode on now; the run starts in 60 s."
  ;;
pull)
  sheet "after (cable back in)"
  $ADB shell cat /data/local/tmp/eyko111-$cond.txt > "$base-instrument.txt"
  $ADB shell cat /data/local/tmp/eyko111-$cond-cpufreq.txt > "$base-cpufreq.txt"
  $ADB logcat -d -s EYKO109 > "$base-logcat.txt"
  dir=/storage/emulated/0/Android/data/com.eykon.memory/files/results
  csv=$($ADB shell ls $dir | grep eyko109-speed | tail -1 | tr -d '\r')
  $ADB pull "$dir/$csv" "$CSV_DIR/$PHONE-$DAY-eyko111-$cond-$csv"
  echo "Pulled: $base-*.txt and $CSV_DIR/$PHONE-$DAY-eyko111-$cond-$csv"
  tail -3 "$base-instrument.txt"
  ;;
hold)
  echo "# $PHONE ($SERIAL), commit $COMMIT, EYKO-111 background kill" > "$base-device.txt"
  sheet "before"
  $ADB logcat -G 16M; $ADB logcat -c
  $ADB shell am instrument -w -e class "$CLS#holdInBackground" -e mode MAPPED_NATIVE -e n 100k -e seconds 300 -e commit "$COMMIT" "$RUNNER" \
    | tee "$base-instrument.txt"
  sheet "after"
  $ADB logcat -d -s EYKO109 > "$base-logcat.txt"
  ;;
esac
