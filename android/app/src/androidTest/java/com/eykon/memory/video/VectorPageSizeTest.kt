package com.eykon.memory.video

import android.content.Context
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.spike.TestVectors
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * EYKO-167, phone part: a larger SQLite page size for the vector tables. The laptop (src/benchmarks/vector_page_size.py)
 * found that 16 KB pages store image vectors in 2,344 B a row instead of 4,106 B, but that a database in WAL mode keeps
 * its page size, and Android switches WAL on when it opens the database. These tests answer what only the phone can:
 * where the app can set the page size, and whether converting an existing 100k-row database works and keeps the
 * search scores bit for bit. Measurement only: results go to logcat (tag EYKO167). Own test database, never memories.db;
 * deleted at the end. Argument: `-e n 100000` (rows for the conversion test).
 */
@RunWith(AndroidJUnit4::class)
class VectorPageSizeTest {

    private val tag = "EYKO167"
    private val name = "eyko167_pagesize.db"
    private val context: Context = ApplicationProvider.getApplicationContext()

    private fun long(db: SupportSQLiteDatabase, sql: String): Long = db.query(sql).use { it.moveToFirst(); it.getLong(0) }
    private fun text(db: SupportSQLiteDatabase, sql: String): String = db.query(sql).use { it.moveToFirst(); it.getString(0) }

    /** PRAGMA page_size=N; execSQL first, a query if Android refuses execSQL for it. Returns how it was sent. */
    private fun setPageSize(db: SupportSQLiteDatabase, size: Int): String =
        runCatching { db.execSQL("PRAGMA page_size=$size"); "execSQL" }
            .getOrElse { db.query("PRAGMA page_size=$size").use { c -> c.moveToFirst() }; "query (execSQL refused: ${it.message})" }

    /** Opened the way Room opens the app's database: the framework helper with write-ahead logging on. */
    private fun open(configure: (SupportSQLiteDatabase) -> Unit = {}): SupportSQLiteOpenHelper {
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = configure(db)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        return FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(name).callback(callback).build())
            .also { it.setWriteAheadLoggingEnabled(true) }
    }

    private fun cleanUp() {
        VideoVectors.clearCache()
        context.getDatabasePath(name).parentFile?.listFiles { f -> f.name.startsWith(name) }?.forEach { it.delete() }
        context.deleteDatabase(name)
    }

    private fun bytesOnDisk(): Long = context.getDatabasePath(name).parentFile!!
        .listFiles { f -> f.name == name || f.name == "$name-wal" || f.name == "$name-shm" }!!.sumOf { it.length() }

    /**
     * A new database, three ways: (1) as the app does it today; (2) PRAGMA page_size=16384 in onConfigure, WAL already on;
     * (3) in onConfigure: WAL off, page size set, then WAL on again after the tables exist. Which one ends at 16 KB?
     */
    @Test
    fun whereTheAppCanSetThePageSizeOfANewDatabase() {
        val found = LinkedHashMap<String, String>()
        for (way in listOf("default", "pragma_in_onConfigure", "wal_off_in_onConfigure")) {
            cleanUp()
            var sent = "-"
            val helper = when (way) {
                "default" -> open()
                "pragma_in_onConfigure" -> open(configure = { sent = setPageSize(it, 16384) })
                else -> open(configure = { it.disableWriteAheadLogging(); sent = setPageSize(it, 16384) })
            }
            try {
                val db = helper.writableDatabase
                if (way == "wal_off_in_onConfigure") db.enableWriteAheadLogging()
                found[way] = "page_size ${long(db, "PRAGMA page_size")}, journal ${text(db, "PRAGMA journal_mode")}, set by $sent"
            } finally {
                helper.close()
            }
            Log.i(tag, "new database, $way: ${found[way]}")
        }
        cleanUp()
        Log.i(tag, "new database summary: $found")
    }

    /**
     * An existing 4 KB database in WAL mode with n image vectors (the app's situation), converted to 16 KB pages:
     * WAL off, PRAGMA page_size, VACUUM, WAL on. Size before and after, VACUUM time, integrity, the page size after
     * reopening, and the app's search scores (VideoVectors, rebuilt from the database) bit for bit before and after.
     */
    @Test
    fun convertAnExisting4KbDatabaseAndKeepTheScores() {
        val n = InstrumentationRegistry.getArguments().getString("n")?.toInt() ?: 100_000
        cleanUp()
        val queries = TestVectors.stream("real", 512, 7L).let { next -> List(20) { next() } }
        var helper = open()
        try {
            var db = helper.writableDatabase
            val next = TestVectors.stream("real", 512, 1L)
            val insertMs = kotlin.system.measureTimeMillis {
                db.beginTransaction()
                try {
                    val statement = db.compileStatement("INSERT INTO image_vec (frame_id, embedding) VALUES (?, ?)")
                    for (i in 1..n) {
                        statement.bindLong(1, i.toLong())
                        statement.bindBlob(2, TestVectors.toBlob(next()))
                        statement.executeInsert()
                    }
                    db.setTransactionSuccessful()
                } finally {
                    db.endTransaction()
                }
            }
            db.query("PRAGMA wal_checkpoint(TRUNCATE)").use { it.moveToFirst() }
            val before = "page_size ${long(db, "PRAGMA page_size")}, journal ${text(db, "PRAGMA journal_mode")}, ${bytesOnDisk()} B on disk"
            VideoVectors.forget(db, "image_vec")
            val scoresBefore = queries.map { VideoVectors.scores(db, "image_vec", it).scores.copyOf() }
            Log.i(tag, "convert: $n rows inserted in $insertMs ms; before: $before")

            db.disableWriteAheadLogging()
            val sent = setPageSize(db, 16384)
            val vacuumMs = kotlin.system.measureTimeMillis { db.execSQL("VACUUM") }
            db.enableWriteAheadLogging()
            val integrity = text(db, "PRAGMA integrity_check")
            val after = "page_size ${long(db, "PRAGMA page_size")}, journal ${text(db, "PRAGMA journal_mode")}, ${bytesOnDisk()} B on disk"
            Log.i(tag, "convert: VACUUM $vacuumMs ms (page size set by $sent); after: $after; integrity $integrity")

            helper.close() // Android sets its default page size again on every open: does the file keep 16 KB?
            helper = open()
            db = helper.writableDatabase
            val reopened = long(db, "PRAGMA page_size")
            VideoVectors.forget(db, "image_vec") // rebuild the search copy from the converted database
            val scoresAfter = queries.map { VideoVectors.scores(db, "image_vec", it).scores.copyOf() }
            val same = scoresBefore.indices.all { scoresBefore[it].contentEquals(scoresAfter[it]) }
            Log.i(tag, "convert: page_size after reopening $reopened; scores bit-identical for ${queries.size} queries: $same; rows ${long(db, "SELECT COUNT(*) FROM image_vec")}")
            assertEquals("ok", integrity)
            assertEquals(n.toLong(), long(db, "SELECT COUNT(*) FROM image_vec"))
            assertTrue("search scores must be bit-identical after the conversion", same)
        } finally {
            helper.close()
            cleanUp()
        }
    }
}
