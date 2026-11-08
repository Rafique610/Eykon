package com.eykon.memory.spike

import android.content.Context
import android.util.Log
import androidx.sqlite.SQLiteConnection
import androidx.sqlite.driver.bundled.BundledSQLiteDriver
import androidx.sqlite.driver.bundled.SQLITE_OPEN_CREATE
import androidx.sqlite.driver.bundled.SQLITE_OPEN_FULLMUTEX
import androidx.sqlite.driver.bundled.SQLITE_OPEN_READWRITE
import androidx.sqlite.execSQL
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import io.requery.android.database.sqlite.SQLiteCustomExtension
import io.requery.android.database.sqlite.SQLiteDatabase
import io.requery.android.database.sqlite.SQLiteDatabaseConfiguration
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.Locale

/**
 * EYKO-106: why is requery (R2) about 2x slower than Google's bundled SQLite (R1) at the same vec0 search?
 * Both engines search the SAME two files (one written by each), after logging their runtime settings.
 * Then requery is searched again with its settings set to Google's values. Tag EYKO31, argument n (100k).
 */
@RunWith(AndroidJUnit4::class)
class RouteR2DiagnoseTest {

    private val tag = "EYKO31"
    private val pragmas = listOf("page_size", "cache_size", "mmap_size", "journal_mode", "locking_mode", "temp_store",
        "cache_spill", "soft_heap_limit", "hard_heap_limit", "threads", "auto_vacuum", "synchronous")
    private val sql = "SELECT rowid FROM image_vec WHERE embedding MATCH ? AND k = 20 ORDER BY distance"

    private fun googleOpen(plugin: String, f: File): SQLiteConnection = BundledSQLiteDriver().apply { addExtension(plugin, "sqlite3_vec_init") }
        .open(f.absolutePath, SQLITE_OPEN_READWRITE or SQLITE_OPEN_CREATE or SQLITE_OPEN_FULLMUTEX)

    private fun requeryOpen(plugin: String, f: File): SQLiteDatabase =
        SQLiteDatabase.openDatabase(SQLiteDatabaseConfiguration(f.absolutePath, SQLiteDatabase.CREATE_IF_NECESSARY or SQLiteDatabase.OPEN_READWRITE)
            .apply { customExtensions.add(SQLiteCustomExtension(plugin, "sqlite3_vec_init")) }, null, null)

    private fun SQLiteConnection.one(q: String): String = prepare(q).closing { if (it.step()) it.getText(0) else "" }
    private fun SQLiteDatabase.one(q: String): String = rawQuery(q, null).use { if (it.moveToFirst()) it.getString(0) ?: "" else "" }

    /** Median of 3 run medians of 20 queries, in ms. */
    private fun time(queries: List<FloatArray>, search: (ByteArray) -> Unit): Double {
        search(TestVectors.toBlob(queries[0]))
        return List(3) { queries.drop(1).map { q -> TestVectors.toBlob(q).let { b -> timeMs { search(b) } } }.sorted()[10] }.sorted()[1]
    }

    private fun googleTime(plugin: String, f: File, queries: List<FloatArray>): Pair<Map<String, String>, Double> = googleOpen(plugin, f).closing { c ->
        val settings = pragmas.associateWith { c.one("PRAGMA $it") }
        settings to c.prepare(sql).closing { st -> time(queries) { b -> st.reset(); st.bindBlob(1, b); while (st.step()) Unit } }
    }

    private fun requeryTime(db: SQLiteDatabase, queries: List<FloatArray>): Double =
        time(queries) { b -> db.rawQuery(sql, arrayOf<Any>(b)).use { c -> while (c.moveToNext()) Unit } }

    @Test
    fun sameFilesBothEngines() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val n = parseSize(InstrumentationRegistry.getArguments().getString("n") ?: "100k")
        val plugin = sqliteVecPlugin(context, "neon").first
        val queries = TestVectors.queries("real", 512, 21)
        val files = mapOf("written-by-google" to context.getDatabasePath("eyko106_diag_g.db"), "written-by-requery" to context.getDatabasePath("eyko106_diag_r.db"))
        files.values.forEach { it.parentFile?.mkdirs(); it.delete() }
        fun rows(write: (Int, ByteArray) -> Unit) { val next = TestVectors.stream("real", 512, 31); for (i in 0 until n) write(i, TestVectors.toBlob(next())) }
        googleOpen(plugin, files.getValue("written-by-google")).closing { c ->
            c.execSQL("CREATE VIRTUAL TABLE image_vec USING vec0(embedding float[512])"); c.execSQL("BEGIN")
            c.prepare("INSERT INTO image_vec(rowid, embedding) VALUES (?, ?)").closing { st -> rows { i, b -> st.bindLong(1, i.toLong()); st.bindBlob(2, b); st.step(); st.reset() } }
            c.execSQL("COMMIT")
        }
        requeryOpen(plugin, files.getValue("written-by-requery")).use { db ->
            db.execSQL("CREATE VIRTUAL TABLE image_vec USING vec0(embedding float[512])"); db.beginTransaction()
            db.compileStatement("INSERT INTO image_vec(rowid, embedding) VALUES (?, ?)").use { st -> rows { i, b -> st.bindLong(1, i.toLong()); st.bindBlob(2, b); st.executeInsert() } }
            db.setTransactionSuccessful(); db.endTransaction()
        }
        for ((name, f) in files) {
            val (google, gMs) = googleTime(plugin, f, queries)
            Log.i(tag, "diag n=$n file $name (%.1f MB): google settings $google".format(Locale.ROOT, f.length() / 1e6))
            requeryOpen(plugin, f).use { db ->
                val requery = pragmas.associateWith { db.one("PRAGMA $it") }
                val differ = pragmas.filter { google[it] != requery[it] }
                Log.i(tag, "diag n=$n file $name: requery settings $requery; differ: $differ")
                val rMs = requeryTime(db, queries)
                for (p in differ.filter { it in listOf("cache_size", "mmap_size", "temp_store", "cache_spill", "soft_heap_limit", "threads", "locking_mode") }) {
                    db.one("PRAGMA $p = ${google.getValue(p)}")
                }
                val rAligned = requeryTime(db, queries)
                Log.i(tag, "diag n=$n file $name: median ms google %.1f, requery %.1f, requery with google's settings %.1f (now ${pragmas.associateWith { db.one("PRAGMA $it") }.filterKeys { it in differ }})".format(Locale.ROOT, gMs, rMs, rAligned))
            }
        }
        files.values.forEach { it.delete() }
    }
}
