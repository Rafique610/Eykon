package com.eykon.memory.video

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.util.Log
import androidx.work.BackoffPolicy
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.eykon.memory.MemoryApp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/**
 * EYKO-44: runs the queued video jobs as WorkManager long-running work with a foreground notification, so they keep going when
 * the app is in the background or swiped from recents, and are started again after a reboot (WorkManager remembers unfinished work).
 * How the stages work does not change: this only calls [VideoWorker.drainWhenIdle].
 *
 * Why no constraints: the work is local (no network), and "only when charging" would stall the one case this card exists for.
 * The cost is battery use while a video is processed; the notification tells the person it is happening.
 */
class VideoJobWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    private val app get() = applicationContext as MemoryApp

    override suspend fun getForegroundInfo(): ForegroundInfo = foregroundInfo("Starting")

    override suspend fun doWork(): Result {
        try {
            return run()
        } catch (e: CancellationException) {
            // Why Android stopped us (EYKO-44 review): shown in `adb logcat -s EykonVideo`, so the phone checks can say which stop it was.
            Log.w(TAG, "worker stopped, reason ${stopReasonName(stopReason)} (code $stopReason)")
            throw e
        }
    }

    private suspend fun run(): Result {
        try {
            setForeground(foregroundInfo("Starting"))
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // Android refuses a foreground service in some states: from the background (API 31+, IllegalStateException) or without the
            // right type or permission (API 34+, SecurityException). Carry on as plain work: saved stages mean that if the system stops us,
            // the job resumes. Never lose the queue over a notification, and say why in the log.
            Log.w(TAG, "foreground service not allowed here, running as plain work: ${e.javaClass.simpleName}: ${e.message}", e)
        }
        return coroutineScope {
            val progress = launchProgressUpdates()
            try {
                // The stages cannot be interrupted, so a stop (cancellation) is honoured at the next stage boundary.
                var ran = true
                withContext(Dispatchers.Default) {
                    do {
                        ran = app.videoWorker.drainWhenIdle { !isActive }
                    } while (ran && isActive && app.videoJobs.hasQueued()) // a job that arrived as the loop ended: go again
                }
                // False: another loop in this process is still working. Try again soon (short linear backoff); a kick that arrives meanwhile
                // is appended (APPEND_OR_REPLACE) rather than ignored.
                if (ran) Result.success() else Result.retry()
            } finally {
                progress.cancel()
            }
        }
    }

    /** Keeps the notification text on the video and stage being worked on. */
    private fun CoroutineScope.launchProgressUpdates() = launch {
        while (isActive) {
            delay(PROGRESS_EVERY_MS)
            val now = app.videoWorker.current
            val text = if (now == null) "Waiting for the next video" else "Video ${now.first.take(8)}: ${now.second}"
            notificationManager().notify(NOTIFICATION_ID, notification(text))
        }
    }

    private fun foregroundInfo(text: String): ForegroundInfo {
        ensureChannel()
        return ForegroundInfo(NOTIFICATION_ID, notification(text), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
    }

    /** Created once per process, not on every notification update. */
    private fun ensureChannel() {
        if (!channelCreated.compareAndSet(false, true)) return
        notificationManager().createNotificationChannel(NotificationChannel(CHANNEL_ID, "Video processing", NotificationManager.IMPORTANCE_LOW))
    }

    private fun notificationManager() = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    private fun notification(text: String): Notification {
        return Notification.Builder(applicationContext, CHANNEL_ID)
            .setContentTitle("Eykon is processing video")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .build()
    }

    companion object {
        const val UNIQUE_NAME = "video-jobs"
        private const val CHANNEL_ID = "video_processing"
        private const val NOTIFICATION_ID = 4401
        private const val PROGRESS_EVERY_MS = 3_000L
        private const val TAG = "EykonVideo"
        private val channelCreated = AtomicBoolean(false)

        /** Readable name for WorkInfo.STOP_REASON_* (API 31+ values; older phones report not-stopped or unknown). */
        fun stopReasonName(code: Int): String = when (code) {
            WorkInfo.STOP_REASON_NOT_STOPPED -> "not stopped"
            WorkInfo.STOP_REASON_CANCELLED_BY_APP -> "cancelled by the app"
            WorkInfo.STOP_REASON_PREEMPT -> "preempted"
            WorkInfo.STOP_REASON_TIMEOUT -> "timeout"
            WorkInfo.STOP_REASON_DEVICE_STATE -> "device state"
            WorkInfo.STOP_REASON_FOREGROUND_SERVICE_TIMEOUT -> "foreground service timeout (Android 15 dataSync limit)"
            WorkInfo.STOP_REASON_APP_STANDBY -> "app standby"
            WorkInfo.STOP_REASON_BACKGROUND_RESTRICTION -> "background restriction"
            WorkInfo.STOP_REASON_USER -> "stopped by the user"
            WorkInfo.STOP_REASON_SYSTEM_PROCESSING -> "system processing"
            WorkInfo.STOP_REASON_ESTIMATED_APP_LAUNCH_TIME_CHANGED -> "launch time changed"
            WorkInfo.STOP_REASON_UNKNOWN -> "unknown"
            else -> "other"
        }
    }
}

/**
 * Starts the video job worker. A request while one is running is appended and runs after it (APPEND_OR_REPLACE), so a video added just as
 * the loop ends is never dropped; the appended turn finds nothing queued and finishes at once if the running one already took the job.
 * (KEEP would ignore the request while the earlier work waits to retry, leaving the video unprocessed for hours.) Only one runs at a time.
 */
object VideoJobScheduler {
    fun enqueue(workManager: WorkManager) {
        val request = OneTimeWorkRequestBuilder<VideoJobWorker>()
            .setBackoffCriteria(BackoffPolicy.LINEAR, 10, TimeUnit.SECONDS)
            .build()
        workManager.enqueueUniqueWork(VideoJobWorker.UNIQUE_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
    }
}
