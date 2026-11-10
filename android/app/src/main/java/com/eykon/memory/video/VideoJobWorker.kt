package com.eykon.memory.video

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.eykon.memory.MemoryApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
            setForeground(foregroundInfo("Starting"))
        } catch (e: IllegalStateException) {
            // Android refuses to start a foreground service from the background in some states (API 31+). Carry on as plain work:
            // saved stages mean that if the system stops us, the job resumes. Never lose the queue over a notification.
            Log.w(TAG, "foreground service not allowed here, running as plain work: ${e.message}")
        }
        return coroutineScope {
            val progress = launchProgressUpdates()
            try {
                val ran = withContext(Dispatchers.Default) { app.videoWorker.drainWhenIdle() }
                when {
                    !ran -> Result.retry() // another loop in this process is still working: try again later
                    // A job that arrived just as the loop ended would be ignored by the unique work (KEEP) while we still run: ask for a second turn.
                    app.videoJobs.hasQueued() -> Result.retry()
                    else -> Result.success()
                }
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

    private fun foregroundInfo(text: String) =
        ForegroundInfo(NOTIFICATION_ID, notification(text), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)

    private fun notificationManager() = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

    private fun notification(text: String): Notification {
        notificationManager().createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Video processing", NotificationManager.IMPORTANCE_LOW),
        )
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
    }
}

/** Starts the video job worker once: a second request while one is queued or running is ignored (ExistingWorkPolicy.KEEP). */
object VideoJobScheduler {
    fun enqueue(workManager: WorkManager) {
        workManager.enqueueUniqueWork(VideoJobWorker.UNIQUE_NAME, ExistingWorkPolicy.KEEP, OneTimeWorkRequestBuilder<VideoJobWorker>().build())
    }
}
