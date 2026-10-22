package com.eykon.memory.video

/**
 * Turns interleaved PCM (any rate, any channel count) into mono at [outRate], a chunk at a time.
 * Channels are averaged. Going down in rate, each output sample is the average of the input
 * samples it covers (a simple low-pass); going up, samples are repeated.
 * Pure Kotlin, so it runs in JVM tests.
 */
class MonoResampler(private val inRate: Int, private val channels: Int, private val outRate: Int = 16_000) {

    private var sum = 0L
    private var count = 0
    private var phase = 0
    private var frame = 0L
    private var inFrame = 0

    /** Feed [length] interleaved samples; [emit] is called once per output sample. */
    fun feed(samples: ShortArray, length: Int, emit: (Short) -> Unit) {
        for (i in 0 until length) {
            frame += samples[i]
            if (++inFrame < channels) continue
            sum += frame / channels
            count++
            frame = 0
            inFrame = 0
            phase += outRate
            while (phase >= inRate) {
                emit((sum / count).toInt().toShort())
                phase -= inRate
            }
            if (phase < outRate) { // the next input sample starts a new output sample
                sum = 0
                count = 0
            }
        }
    }
}
