"""EYKO-116 part 3: kill the app in the middle of a pipeline stage, reopen it, and log what the job does.

Usage:  python -I scripts/eyko116_kill.py --stage scene --delay 5 --log docs/results/vectors/crash/infinix-<date>-kill-scene-run1.txt
Add the clip to the app first (it must be processing). The script reads the app's own log (tag EykonVideo). A stage writes its
log line when it ENDS, so the script waits for the line that ends the stage before the one to hit, waits --delay seconds, and runs
`am force-stop com.eykon.memory`. It then reopens the app (launcher intent, the Eykon app only) and keeps reading until the video
reaches "finish ... ready", a failure line shows up, or --wait seconds pass. Everything it saw is written to --log, with times.
Stage order: split, filter, dedup, scene, small_objects, embed_images, embed_texts, link, latest.
"""
import argparse
import datetime
import re
import subprocess
import time

ORDER = ["split", "filter", "dedup", "scene", "small_objects", "embed_images", "embed_texts", "link", "latest"]
LINE = re.compile(r"EykonVideo\s*:\s*(\w+)\s+([0-9a-f]{32})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default=r"C:\platform-tools\adb.exe")
    ap.add_argument("--stage", required=True, choices=ORDER[1:], help="stage to kill the app inside")
    ap.add_argument("--delay", type=float, default=5, help="seconds after the previous stage's end line")
    ap.add_argument("--wait", type=int, default=900, help="seconds to keep watching after the reopen")
    ap.add_argument("--log", required=True)
    a = ap.parse_args()
    previous = ORDER[ORDER.index(a.stage) - 1]
    out = open(a.log, "w", encoding="utf-8")

    def say(text: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"{stamp} {text}")
        out.write(f"{stamp} {text}\n")
        out.flush()

    say(f"waiting for the end of '{previous}' to kill inside '{a.stage}' (delay {a.delay}s)")
    p = subprocess.Popen([a.adb, "logcat", "-v", "time", "-s", "EykonVideo"], stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    killed = False
    reopened_at = None
    video = None
    try:
        for raw in p.stdout:
            line = raw.rstrip()
            if not line or line.startswith("---"):
                continue
            out.write("   | " + line + "\n")
            m = LINE.search(line)
            stage = m.group(1) if m else None
            if m and video is None:
                video = m.group(2)
            if not killed and stage == previous:
                time.sleep(a.delay)
                subprocess.run([a.adb, "shell", "am", "force-stop", "com.eykon.memory"])
                killed = True
                say(f"force-stopped after the '{previous}' line (video {m.group(2)[:8]}), delay {a.delay}s: inside '{a.stage}'")
                time.sleep(3)
                alive = subprocess.run([a.adb, "shell", "pidof", "com.eykon.memory"], capture_output=True, text=True).stdout.strip()
                say(f"app process after the kill: {alive or 'none (killed)'}")
                subprocess.run([a.adb, "shell", "monkey", "-p", "com.eykon.memory", "-c", "android.intent.category.LAUNCHER", "1"], capture_output=True)
                reopened_at = time.time()
                say("reopened the app")
            if killed and "finish" in line and "ready" in line:
                say("RESULT: the video reached ready after the reopen")
                break
            if killed and re.search(r"fail|error|exception", line, re.I):
                say("note: failure/error line seen after the kill (see log)")
            if reopened_at and time.time() - reopened_at > a.wait:
                say(f"RESULT: no 'ready' within {a.wait}s after the reopen")
                break
    finally:
        p.terminate()
        out.close()


if __name__ == "__main__":
    main()
