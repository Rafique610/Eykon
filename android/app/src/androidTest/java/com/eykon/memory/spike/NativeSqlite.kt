package com.eykon.memory.spike

/**
 * EYKO-108 (route R4, throwaway): the smallest JNI layer over our own SQLite build (cpp/r4_jni.c).
 * sqlite-vec is compiled in and registered in JNI_OnLoad. Load one build per process:
 * `eykon_r4` (NEON) or `eykon_r4_noneon`.
 */
object NativeSqlite {
    const val ROW = 100
    const val DONE = 101

    fun load(neon: Boolean) = System.loadLibrary(if (neon) "eykon_r4" else "eykon_r4_noneon")

    @JvmStatic external fun nativeOpen(path: String): Long
    @JvmStatic external fun nativeClose(db: Long)
    @JvmStatic external fun nativeErrmsg(db: Long): String
    @JvmStatic external fun nativeExec(db: Long, sql: String): String?
    @JvmStatic external fun nativePrepare(db: Long, sql: String): Long
    @JvmStatic external fun nativeStep(stmt: Long): Int
    @JvmStatic external fun nativeReset(stmt: Long): Int
    @JvmStatic external fun nativeFinalize(stmt: Long)
    @JvmStatic external fun nativeBindLong(stmt: Long, index: Int, value: Long): Int
    @JvmStatic external fun nativeBindDouble(stmt: Long, index: Int, value: Double): Int
    @JvmStatic external fun nativeBindBlob(stmt: Long, index: Int, value: ByteArray): Int
    @JvmStatic external fun nativeBindText(stmt: Long, index: Int, value: String): Int
    @JvmStatic external fun nativeColumnLong(stmt: Long, index: Int): Long
    @JvmStatic external fun nativeColumnDouble(stmt: Long, index: Int): Double
    @JvmStatic external fun nativeColumnText(stmt: Long, index: Int): String?
    @JvmStatic external fun nativeColumnBlob(stmt: Long, index: Int): ByteArray?

    /** Runs [sql] and returns the first column of the first row as text (versions, counts). */
    fun scalar(db: Long, sql: String): String? {
        val st = nativePrepare(db, sql)
        check(st != 0L) { "prepare failed: ${nativeErrmsg(db)} for $sql" }
        try {
            return if (nativeStep(st) == ROW) nativeColumnText(st, 0) else null
        } finally {
            nativeFinalize(st)
        }
    }
}
