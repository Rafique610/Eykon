package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Runs queued jobs one at a time, stage by stage, saving the stage reached so a job
 * can resume. It works only while there are jobs: no polling when the queue is empty.
 */
class VideoWorker(
    private val db: () -> SupportSQLiteDatabase,
    private val jobs: VideoJobs,
    private val stages: List<Pair<String, Stage>> = VideoPipeline.STAGES,
    private val retries: Int = RETRIES,
) {
    private val draining = AtomicBoolean(false)

    /** Run one job. False when the queue is empty. */
    fun runOnce(): Boolean {
        val job = jobs.claim() ?: return false
        try {
            for ((name, stage) in stagesAfter(job.stage)) {
                stage(db(), job.videoId)
                jobs.stageDone(job.id, name)
            }
            jobs.done(job.id)
        } catch (e: Exception) {
            // Class and a short message only: never a stack trace in the database.
            jobs.attemptFailed(job, "${e.javaClass.simpleName}: ${e.message.orEmpty().take(200)}".trimEnd(':', ' '), retries)
        }
        return true
    }

    fun drain() {
        while (runOnce()) Unit
    }

    /** Start working through the queue in the background, unless that is already happening. */
    fun kick(scope: CoroutineScope) {
        if (!draining.compareAndSet(false, true)) return
        scope.launch {
            try {
                drain()
            } finally {
                draining.set(false)
            }
            if (jobs.hasQueued()) kick(scope) // a job arrived just as the loop was ending
        }
    }

    private fun stagesAfter(doneStage: String): List<Pair<String, Stage>> {
        val index = stages.indexOfFirst { it.first == doneStage }
        return if (index >= 0) stages.drop(index + 1) else stages
    }

    companion object {
        const val RETRIES = 3
    }
}
