package com.eykon.memory

import android.app.Application
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.data.MemoryDatabase
import com.eykon.memory.video.VideoJobs
import com.eykon.memory.video.VideoJobScheduler
import com.eykon.memory.video.VideoPipeline
import com.eykon.memory.video.VideoWorker
import androidx.work.WorkManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class MemoryApp : Application() {

    val database: MemoryDatabase by lazy {
        MemoryDatabase.getInstance(this)
    }

    /** Lives as long as the app process: video jobs keep running when the person leaves the screen. */
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val videoDb: () -> SupportSQLiteDatabase = { database.openHelper.writableDatabase }
    val videoJobs: VideoJobs by lazy { VideoJobs(videoDb) }
    val videoWorker: VideoWorker by lazy { VideoWorker(videoDb, videoJobs) }

    /**
     * Start working through queued video jobs. EYKO-44: through WorkManager as long-running work with a foreground notification (see
     * VideoJobWorker), so it carries on with the app in the background or closed. No timer, no polling: called when a job is added or the app starts.
     */
    fun kickVideoWorker() = VideoJobScheduler.enqueue(WorkManager.getInstance(this))

    override fun onCreate() {
        super.onCreate()
        instance = this
        applicationScope.launch {
            // Jobs cut short when the app last stopped. Harmless next to the WorkManager worker: only one loop runs at a time (VideoWorker.drainWhenIdle),
            // so a job this puts back to queued while the loop is already working on it is finished by that same loop and never claimed a second time.
            videoJobs.requeueInterrupted()
            val prefs = getSharedPreferences("video_pipeline", MODE_PRIVATE)
            val redoAfter = VideoPipeline.redoAfter(prefs.getInt("version", 1))
            if (redoAfter != null) { // a middle stage changed: redo finished videos once
                videoJobs.requeueAfter(redoAfter)
                prefs.edit().putInt("version", VideoPipeline.VERSION).apply()
            }
            videoJobs.requeueBehind(VideoPipeline.STAGES.last().first) // videos processed before newer stages existed
            kickVideoWorker()
        }
    }

    companion object {
        lateinit var instance: MemoryApp
            private set
    }
}
