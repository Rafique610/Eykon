# Head 3 research: Android background-work rules and the intake limits (16 Nov 2026)

Card EYKO-122. Head 3 questions D1 and A5. Reading only, no new tests: every claim links to an Android page or to one of our own
result files. Pages were read on 16 Nov 2026.

**The card changed after it was written (10 Nov).** D1 asked "why an in-app thread and not WorkManager?". Since then EYKO-44 moved
video jobs to WorkManager (long-running worker, `dataSync` foreground service), checked on the Infinix (Android 13) and the Pixel
(Android 17). A5 asked where the 500 MB limit comes from. EYKO-126 then removed it for the normal path (the gallery file is read in
place), and it is now used only when the phone will not keep the read permission and the file is copied
(`android/.../video/VideoCapture.kt`, `VideoMetadata.MAX_MB = 500`). So this file answers: what limits the WorkManager job on
Android 12 to 17, and which file types and size limit we still need.

Our app: `minSdk 31` (Android 12), `targetSdk 35` (Android 15), WorkManager 2.10.0, service type `dataSync`
(`android/app/src/main/AndroidManifest.xml`, `VideoJobWorker.kt`).

## Part 1: what limits a long video job

| Option | Limit (source) | What happens to our job | Measured by us |
|---|---|---|---|
| In-app thread (before EYKO-44) | No Android protection at all. A background process with high CPU use can be killed. | Killed: `excessive cpu ... limit=2` after 26 min of work in the background, 11 Nov ([EYKO-44 Infinix](../results/2026-11-12-eyko44-workmanager-phone-checks.md), [storage-and-crash](../results/2026-11-09-storage-and-crash.md)). It also ran only while the app was in front: 8 min of video took 21.2 min instead of about 13 ([ego4d-baseline](../results/2026-10-20-ego4d-baseline.md)). | yes |
| WorkManager, plain worker (no foreground service) | It runs on JobScheduler. Doze "Doesn't let JobScheduler run. WorkManager uses JobScheduler internally, so WorkManager tasks don't run." ([Doze](https://developer.android.com/training/monitoring-device-state/doze-standby)). Run time is set by the standby bucket: Active "Up to 20 minutes in a rolling 60 minute period", Working set "Up to 10 minutes in a rolling 4 hour period", Rare "Up to 10 minutes in a rolling 24 hour period", Restricted "Once per day for up to 10 minutes" ([power details](https://developer.android.com/topic/performance/power/power-details)). Workers that need more must be long-running: "These Workers can run longer than 10 minutes." ([long-running workers](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)) | Our fallback when the foreground service is refused. Saved stages mean a stopped job resumes, but a 25 min clip (92 min of work on the Infinix) would take many windows, possibly days in the Rare bucket. | the fallback ran once, after the jobs were done ([EYKO-44 Infinix, check 4](../results/2026-11-12-eyko44-workmanager-phone-checks.md)) |
| **WorkManager long-running worker + `dataSync` foreground service (now)** | Android 12+: "Apps that target Android 12 (API level 31) or higher can't start foreground services while the app is running in the background, except for a few special cases", else `ForegroundServiceStartNotAllowedException` ([background start](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)). Android 14+: "you must declare an appropriate service type for each foreground service" ([types](https://developer.android.com/develop/background-work/services/fgs/service-types)). **Android 15+ (we target it):** "The system permits `dataSync` and `mediaProcessing` foreground services to run for a total of 6 hours in a 24-hour period"; then `Service.onTimeout()` and "a few seconds to call `Service.stopSelf()`", else a crash; "if the user brings the app to the foreground, the timer resets" ([timeout](https://developer.android.com/develop/background-work/services/fgs/timeout)). Android 16+: "jobs that are executing concurrently with a foreground service will adhere to the job runtime quota" ([16 changes](https://developer.android.com/about/versions/16/behavior-changes-all)); "long running workers (which use foreground services) can exhaust your app's job quota" ([long-running workers](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)). Android 17: nothing new for jobs or services; only background audio changes ([17 changes](https://developer.android.com/about/versions/17/behavior-changes-all)). | Works. The job keeps going in the background, after a swipe from recents, and in deep Doze with the screen off. 6 h a day is about 205 min of video on the Infinix (1.75 min of work per min of video) and about 690 min on the Pixel (0.52). Opening the app resets the 6 h. | Infinix: 55 min of video in 96 min, never killed ([EYKO-44](../results/2026-11-12-eyko44-workmanager-phone-checks.md)). Pixel Android 17: 8 min clip in 4 min in deep Doze ([EYKO-85](../results/2026-11-15-eyko85-background-long-clip.md)). 6 h limit not reached by any test. |
| `mediaProcessing` foreground service (Android 15+) | Permission `FOREGROUND_SERVICE_MEDIA_PROCESSING`, no runtime prerequisite ([types](https://developer.android.com/develop/background-work/services/fgs/service-types)). Same 6 h in 24 h, and "The six-hour time limit is tracked separately for `dataSync` and for `mediaProcessing` services" ([timeout](https://developer.android.com/develop/background-work/services/fgs/timeout)). Added in Android 15, so phones on 12 to 14 still need `dataSync`. | Same behaviour as now. It is the type that describes our work (decoding and processing video on the phone; `dataSync` is for moving data). | no |
| User-initiated data transfer job | "exempt from the ordinary job quotas", meant for "user-initiated downloads" ([long-running workers](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)) | Does not fit: our job is local processing, not a network transfer. | no |
| Doze and App Standby | A process "currently in the foreground, either as an activity or foreground service" is not treated as idle; "Don't start a foreground service just to prevent the system from determining that your app is idle." ([Doze](https://developer.android.com/training/monitoring-device-state/doze-standby)). Restricted bucket: "You can run jobs once per day in a 10-minute batched session", and its limits apply "even when the device is charging" ([App Standby](https://developer.android.com/topic/performance/appstandby)). Jobs in a process with a foreground service: "Execution limits are enforced based on the standby bucket" ([power details](https://developer.android.com/topic/performance/power/power-details)). | A job the user just started has the app in Active, so this matters only for old queued work or an app Android has put in Restricted. | deep Doze did not stop the job (EYKO-85) |
| Extreme Battery Saver (Pixel) | Not an Android developer rule; a Pixel setting. | **Eykon is paused completely** (`suspended=true`). | yes (EYKO-85) |
| Samsung (One UI) | "By default any app which is not started in 3 days is put to sleep and background tasks including alarms will stop working"; "Since One UI 6.0, foreground services of apps targeting Android 14 will be guaranteed to work as intended so long as they are developed according to Android's new foreground service API policy." Fix: turn off "Put unused apps to sleep", set the app to "Don't optimize" ([dontkillmyapp Samsung](https://dontkillmyapp.com/samsung)). | Our A32 (SM-A325F) runs One UI on Android 13; a queue left for 3+ days could sleep. | not tested on the A32 |
| Xiaomi (MIUI / HyperOS) | Autostart is denied by default and "Battery Saver" kills services; the fix is Autostart on and App battery saver "No restriction" ([dontkillmyapp Xiaomi](https://dontkillmyapp.com/xiaomi), read through search results only: the page could not be fetched; [AdGuard guide](https://adguard.com/kb/adguard-for-android/solving-problems/background-work/)). | No Xiaomi phone in the team. | no |
| Infinix / Tecno (Transsion, XOS) | No dontkillmyapp page for Infinix was found. Support guides point to Phone Master > Auto-start Management ([Salestrail](https://www.salestrail.io/knowledge-base/infinix-devices)); [CommCare](https://dimagi.atlassian.net/wiki/spaces/commcarepublic/pages/2575794214) notes the same issue across Transsion brands. Secondary sources. | After a reboot mid-job the saved work **did not start until the app was opened**; on the Pixel it started by itself 47 s after unlock. Cause likely auto-start, **not proven**. | yes ([EYKO-44 Infinix, check D](../results/2026-11-12-eyko44-workmanager-phone-checks.md), [EYKO-44 Pixel](../results/2026-11-15-eyko44-pixel-checks.md)) |
| Pixel (stock Android) | Follows the Android rules above. | Background, reboot and deep Doze all work. | yes |

### Recommendation (D1)

**Keep WorkManager long-running work with a foreground service; it is the right choice and our phone tests back it.** Three small
follow-ups, each its own card if the owner agrees:

1. **Declare `mediaProcessing` on Android 15+ and keep `dataSync` on 12 to 14.** It is the type that matches the work, with the same
   6 h rule. Do not use both at once to get 12 h: that is using the rules against their intent.
2. **Handle the 6 h timeout on purpose.** The worker already logs the stop reason. Add a check that a job stopped by the timeout
   resumes when the app is next opened (the timer resets then). It cannot be tested on the Infinix (Android 13); it needs the
   Pixel and a long queue, or a shortened limit through `adb` if Android allows it.
3. **Tell the user about phone-maker settings** on Transsion, Xiaomi and Samsung phones (`Build.MANUFACTURER`): auto-start,
   battery "Unrestricted", and Samsung's sleeping apps. Zara's phone can show whether allowing auto-start fixes check D.

## Part 2: file types and the size limit

### How much video 500 MB is

The limit is `500 × 1024 × 1024` = 524,288,000 bytes.

| Recording | Bitrate | Per minute | 500 MB lasts | Source |
|---|---|---|---|---|
| Pixel kit clip, 1080p HEVC | 20.0 Mbps (186,496,596 B / 74.5 s) | 150 MB | **3.5 min** | our file ([read-from-gallery](../results/2026-11-13-read-from-gallery.md)) |
| Pixel, 8-minute loop of that clip | 20.0 Mbps (1,197,672,204 B / 480 s) | 150 MB | 3.5 min | our file ([EYKO-85](../results/2026-11-15-eyko85-background-long-clip.md)) |
| Pixel 6, 4K30 H.264 | 48 Mbps | 360 MB | 1.5 min | [GSMArena review](https://www.gsmarena.com/google_pixel_6-review-2350p6.php) |
| Pixel 4, 1080p30 / 4K30 | file sizes 130 / 350 MB per min | 130 / 350 MB | 4.0 / 1.5 min | [Android Central](https://www.androidcentral.com/pixel-4-doesnt-support-4k-60fps-because-it-uses-too-much-space) (seen in search results) |
| Samsung A32 | not measured, no source found | | | gap |

So **500 MB is 1.5 to 4 minutes of phone camera video.** It is not a sensible cap on what a person records. It was a copy limit (storage
for the copy), and in-place reading took the copy away.

### Which file types Android reads

Android's [supported media formats](https://developer.android.com/media/platform/supported-formats) list H.264 (in .3gp, .mp4, .ts,
.mkv), H.265 HEVC "Android 5.0+" (in .mp4, .mkv), VP8 (in .webm, .mkv), VP9 (in .webm, .mkv, .mp4), AV1 "Android 10+" (in .mp4, .mkv),
and MPEG-4 SP (in .mp4). The page warns that "a particular mobile device might support additional formats or file types that are not
listed". The [Android 15 CDD](https://source.android.com/docs/compatibility/15/android-15-cdd) says "Handheld device implementations
MUST support the following video decoding formats": H.264, H.265 HEVC, MPEG-4 SP, VP8, VP9 and AV1. **Neither page lists AVI or
QuickTime (.mov).**

| Type | Android lists it | The app today | Our test | Recommendation |
|---|---|---|---|---|
| .mp4 (H.264, HEVC, AV1) | yes | accepted | works (all kit clips) | keep |
| .mov | no (works in practice: same ISO file layout as mp4) | accepted | works on both phones (B10a) | keep, say it is tested, not guaranteed |
| .m4v | no (an mp4 by another name) | accepted | works (B10b) | keep |
| .avi | **no** | accepted | **fails on both phones** (B10c: "This file does not contain a video that can be read") | **remove from the list** (bug 2 in [bad inputs](../results/2026-11-12-head3-bad-inputs.md)) |
| .3gp | yes (H.264, H.263) | refused | not tried | add, test one file |
| .mkv | yes | refused (B11, clear message) | refused | add, test one file |
| .webm | yes (VP8, VP9) | refused | not tried | add, test one file (screen recorders and web downloads use it) |
| .ts | yes, but "not seekable" | refused | not tried | leave out: we seek to take frames |

Sources for B10a to B11: [bad inputs](../results/2026-11-12-head3-bad-inputs.md) (Infinix) and
[intake on two phones](../results/2026-11-15-head3-intake-two-phones.md) (Pixel).

### Recommendation (A5)

1. **No size limit on the in-place path** (as now). The real limits are the 6 h foreground time per day (Part 1) and free space for
   the few MB the app keeps per video (about 126 MB per hour of video, [read-from-gallery](../results/2026-11-13-read-from-gallery.md)).
2. **On the copy path, base the limit on free space, not 500 MB.** The copy already stops when free space runs out
   (`VideoCopy.copyAndHash`). A fixed 500 MB refuses anything over 3.5 min from a Pixel. A margin such as "keep 1 GB free after the
   copy" says what the limit protects.
3. **A length limit is not needed for Android's sake.** If one is wanted, base it on the 6 h rule: a video that needs more than 6 h
   of work on the slowest phone (about 205 min of video on the Infinix) cannot finish in one day without the app being opened.
4. **Accept the types Android lists for decoding:** mp4, m4v, mov (tested), 3gp, mkv, webm. Drop avi. Change the
   "Use one of: ..." message to match.

## Not read or not known

- dontkillmyapp.com's Xiaomi, Google and Infinix pages could not be fetched from this laptop; the Xiaomi lines come from search
  results and other guides.
- The CDD's recommended encoder bitrates (section 5.2) were not reached in the page; the bitrates above are from our own files and
  reviews.
- Whether WorkManager's `setForeground()` from a running worker counts as an exemption to the Android 12 background-start rule. The
  Android page does not say. Zara's check 4 saw the refusal once, at the end of a queue.
- The A32's (One UI) behaviour with the queue: not tested.
