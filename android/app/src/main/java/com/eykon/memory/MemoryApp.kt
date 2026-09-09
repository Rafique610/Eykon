package com.eykon.memory

import android.app.Application
import com.eykon.memory.data.MemoryDatabase

class MemoryApp : Application() {

    val database: MemoryDatabase by lazy {
        MemoryDatabase.getInstance(this)
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    companion object {
        lateinit var instance: MemoryApp
            private set
    }
}
