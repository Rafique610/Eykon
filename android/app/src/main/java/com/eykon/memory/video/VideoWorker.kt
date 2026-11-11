package com.eykon.memory.video

import androidx.sqlite.db.SupportSQLiteDatabase
import kotlinx.coroutines.CancellationException
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

    /** The video and stage being worked on right now (EYKO-44 shows it in the notification); null between jobs. */
    @Volatile
    var current: Pair<String, String>? = null
        private set

    /**
     * Run one job. False when the queue is empty. [shouldStop] is checked before every stage: the stages are blocking and cannot be
     * interrupted, so a stop (EYKO-44) takes effect at the next stage boundary, not in the middle of one.
     */
    fun runOnce(shouldStop: () -> Boolean = { false }): Boolean {
        val job = jobs.claim() ?: return false
        try {
            for ((name, stage) in stagesAfter(job.stage)) {
                if (shouldStop()) throw CancellationException("stop requested before stage $name")
                current = job.videoId to name
                stage(db(), job.videoId)
                jobs.stageDone(job.id, name)
            }
            jobs.done(job.id)
        } catch (e: CancellationException) {
            current = null
            throw e // being stopped is not a failed attempt: the job stays `running` and is requeued the next time the app or the worker starts
        } catch (e: Exception) {
            // Class and a short message only: never a stack trace in the database.
            jobs.attemptFailed(job, "${e.javaClass.simpleName}: ${e.message.orEmpty().take(200)}".trimEnd(':', ' '), retries)
        }
        current = null
        return true
    }

    /**
     * EYKO-44: one loop at a time in this process, whoever asks (the old in-app `kick` or the WorkManager worker). Requeues jobs cut short by an
     * earlier stop, then works through the queue. False when another loop is already running (it must not be requeued while it works).
     */
    fun drainWhenIdle(shouldStop: () -> Boolean = { false }): Boolean {
        if (!draining.compareAndSet(false, true)) return false
        try {
            jobs.requeueInterrupted()
            drain(shouldStop)
        } catch (e: CancellationException) {
            // stopped between stages: the saved stage is kept, nothing to do
        } finally {
            current = null
            draining.set(false)
        }
        return true
    }

    fun drain(shouldStop: () -> Boolean = { false }) {
        while (!shouldStop() && runOnce(shouldStop)) Unit
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
