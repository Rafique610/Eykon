package com.eykon.memory.capture

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

/**
 * High-accuracy on-device speech recognizer utilizing Android's SpeechRecognizer API.
 * Uses on-device recognition model on Android 12+ (API 31+) with EXTRA_PREFER_OFFLINE.
 */
class NativeSpeechRecognizer(private val context: Context) {

    companion object {
        private const val TAG = "NativeSpeechRecognizer"
    }

    private var speechRecognizer: SpeechRecognizer? = null

    @Volatile
    var isListening: Boolean = false
        private set

    /**
     * Starts listening for voice input.
     * Must be called on the Main thread.
     */
    fun startListening(
        onPartialResult: (String) -> Unit,
        onFinalResult: (String) -> Unit,
        onError: (String) -> Unit
    ) {
        if (isListening) return

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            onError("Speech recognition not available on this device")
            return
        }

        try {
            destroy()

            val recognizer = if (SpeechRecognizer.isOnDeviceRecognitionAvailable(context)) {
                SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
            } else {
                SpeechRecognizer.createSpeechRecognizer(context)
            }

            speechRecognizer = recognizer

            recognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    Log.d(TAG, "onReadyForSpeech")
                    isListening = true
                }

                override fun onBeginningOfSpeech() {
                    Log.d(TAG, "onBeginningOfSpeech")
                }

                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}

                override fun onEndOfSpeech() {
                    Log.d(TAG, "onEndOfSpeech")
                    isListening = false
                }

                override fun onError(error: Int) {
                    isListening = false
                    val errorMsg = when (error) {
                        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                        SpeechRecognizer.ERROR_CLIENT -> "Client error"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
                        SpeechRecognizer.ERROR_NETWORK -> "Network error (offline speech model not active)"
                        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                        SpeechRecognizer.ERROR_NO_MATCH -> "No speech recognized. Please speak clearly."
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Speech service busy"
                        SpeechRecognizer.ERROR_SERVER -> "Recognition server error"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech detected"
                        else -> "Speech error ($error)"
                    }
                    Log.w(TAG, "Recognition error ($error): $errorMsg")
                    onError(errorMsg)
                }

                override fun onResults(results: Bundle?) {
                    isListening = false
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull()?.trim().orEmpty()
                    if (text.isNotEmpty()) {
                        Log.i(TAG, "Transcribed final result: $text")
                        onFinalResult(text)
                    } else {
                        onError("No speech recognized")
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull()?.trim().orEmpty()
                    if (text.isNotEmpty()) {
                        Log.d(TAG, "Partial result: $text")
                        onPartialResult(text)
                    }
                }

                override fun onEvent(eventType: Int, params: Bundle?) {}
            })

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            }

            recognizer.startListening(intent)
            isListening = true
        } catch (e: Exception) {
            isListening = false
            Log.e(TAG, "Failed to start recognition: ${e.message}", e)
            onError("Failed to start speech recognition: ${e.message}")
        }
    }

    /**
     * Stops listening and triggers processing of whatever speech was recorded.
     */
    fun stopListening() {
        try {
            speechRecognizer?.stopListening()
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping recognizer: ${e.message}")
        }
        isListening = false
    }

    /**
     * Cleans up recognizer resources.
     */
    fun destroy() {
        try {
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error destroying recognizer: ${e.message}")
        }
        speechRecognizer = null
        isListening = false
    }
}
