package com.eykon.memory.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.video.VideoSchema

/**
 * Room SQLite Database for the Eykon persistent memory application.
 */
@Database(
    entities = [MemoryRecord::class],
    version = 2,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class MemoryDatabase : RoomDatabase() {

    abstract fun memoryDao(): MemoryDao

    companion object {
        private const val DATABASE_NAME = "memories.db"

        @Volatile
        private var INSTANCE: MemoryDatabase? = null

        internal val roomCallback = object : RoomDatabase.Callback() {
            override fun onCreate(db: SupportSQLiteDatabase) {
                super.onCreate(db)
                createFtsTableAndTriggers(db)
                VideoSchema.create(db)
            }

            override fun onOpen(db: SupportSQLiteDatabase) {
                super.onOpen(db)
                createFtsTableAndTriggers(db)
                VideoSchema.create(db)
                // Off by default in SQLite; the video tables rely on ON DELETE CASCADE.
                db.execSQL("PRAGMA foreign_keys = ON")
            }

            private fun createFtsTableAndTriggers(db: SupportSQLiteDatabase) {
                try {
                    db.execSQL("CREATE VIRTUAL TABLE IF NOT EXISTS `memories_fts` USING fts4(`text`, content=`memories`)")
                    
                    db.execSQL("""
                        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                          INSERT INTO memories_fts(docid, text) VALUES (new.id, new.text);
                        END;
                    """.trimIndent())
                    
                    // fts4 has no ('delete', ...) command (that is FTS5), so these triggers
                    // failed on the phone. Same fix as VideoSchema: plain DELETE before the row changes.
                    // Phones that already have the broken triggers: drop them by name first.
                    // One transaction: if a create fails, the drops roll back too.
                    db.beginTransaction()
                    try {
                        db.execSQL("DROP TRIGGER IF EXISTS memories_ad")
                        db.execSQL("DROP TRIGGER IF EXISTS memories_au")

                        db.execSQL("""
                            CREATE TRIGGER IF NOT EXISTS memories_fts_bd BEFORE DELETE ON memories BEGIN
                              DELETE FROM memories_fts WHERE docid = old.id;
                            END;
                        """.trimIndent())

                        db.execSQL("""
                            CREATE TRIGGER IF NOT EXISTS memories_fts_bu BEFORE UPDATE ON memories BEGIN
                              DELETE FROM memories_fts WHERE docid = old.id;
                            END;
                        """.trimIndent())

                        db.execSQL("""
                            CREATE TRIGGER IF NOT EXISTS memories_fts_au AFTER UPDATE ON memories BEGIN
                              INSERT INTO memories_fts(docid, text) VALUES (new.id, new.text);
                            END;
                        """.trimIndent())
                        db.setTransactionSuccessful()
                    } finally {
                        db.endTransaction()
                    }

                    // Sync any memories inserted before FTS table creation
                    db.execSQL("""
                        INSERT INTO memories_fts(docid, text)
                        SELECT id, text FROM memories
                        WHERE id NOT IN (SELECT docid FROM memories_fts);
                    """.trimIndent())
                } catch (t: Throwable) {
                    android.util.Log.w("MemoryDatabase", "FTS initialization failed or not supported by device SQLite: ${t.message}")
                }
            }
        }

        fun getInstance(context: Context): MemoryDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    MemoryDatabase::class.java,
                    DATABASE_NAME
                )
                    .fallbackToDestructiveMigration()
                    .addCallback(roomCallback)
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
