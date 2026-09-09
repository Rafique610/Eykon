# Step 01 — Android Project Setup + Room Storage

**Status:** 🔲 Not started  
**Depends on:** Nothing  
**Blocks:** Everything

---

## What This Step Does

Creates the Android project skeleton (Kotlin, Jetpack Compose) and ports the
Phase 1 storage layer (MemoryRecord shape, schema, CRUD) to Android Room.

## Why This Matters

Same reasoning as Phase 1 Step 01 — every later step depends on storage being
correct. Porting the already-validated schema, rather than redesigning it,
avoids re-litigating decisions Phase 1 already settled.

---

## What Gets Created

```
android/
├── app/
│   ├── src/main/java/com/eykon/memory/
│   │   ├── MemoryApp.kt               ← Application class
│   │   ├── MainActivity.kt            ← empty Compose shell for now
│   │   ├── data/
│   │   │   ├── MemoryRecord.kt        ← Room @Entity, mirrors Phase 1 dataclass
│   │   │   ├── MemoryDao.kt           ← CRUD (save, getAll, getById, delete, count)
│   │   │   ├── MemoryDatabase.kt      ← Room database setup + TypeConverters
│   │   │   └── Converters.kt          ← TypeConverter for JSON embedding ↔ List<Float>
│   │   └── ui/
│   │       └── theme/                  ← Material3 theme stub
│   ├── build.gradle.kts                ← Room, Kotlin coroutines, Compose dependencies
│   └── src/androidTest/java/.../
│       └── MemoryDaoTest.kt           ← Instrumented test for Room round-trip
├── build.gradle.kts                    ← Project-level Gradle
├── settings.gradle.kts
├── gradle.properties
└── local.properties
```

---

## ⚖️ Decisions to Make

### 1. Embedding storage format: BLOB vs JSON string (in SQLite)

Phase 1 used **SQLite** (`memories.db`), storing the embedding vector as a JSON-serialized string inside a `TEXT` column for debuggability and inspection. Room is an abstraction directly over SQLite, so it will manage the same SQLite database. Room can store embeddings either as a BLOB (ByteArray) or a TEXT column with a TypeConverter.

| Approach | Pros | Cons |
|---|---|---|
| JSON string (TEXT column) | Matches Phase 1 SQLite schema, inspectable in Database Inspector, consistent | Slightly larger on disk |
| Binary BLOB (ByteArray) | Compact | Not human-readable, breaks exact schema consistency with Phase 1 |

**Recommendation:** Keep the JSON-string approach for consistency with Phase 1's SQLite schema and easy inspection in Android Studio Database Inspector.

---

### 2. Schema fields — what to port

Port exactly what Phase 1's SQLite schema landed on (`src/memories/database.py`):

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER (PK, auto) | Room `@PrimaryKey(autoGenerate = true)` |
| `text` | TEXT | The raw memory content or transcript |
| `embedding` | TEXT (JSON) | 384-float vector, JSON-encoded string |
| `timestamp` | TEXT (ISO 8601) | When the memory was created |
| `source_type` | TEXT | "text" or "audio" |
| `metadata` | TEXT (JSON) | `{"chunk_index": 0, "total_chunks": 1, "token_count": 42}` |

Don't add new fields speculatively. This matches the Phase 1 final SQLite schema including chunk metadata from Phase 1.1.

**Recommendation:** Port all 6 fields exactly. Use `@ColumnInfo` annotations with explicit column names matching the Phase 1 SQLite schema.

---

### 3. Coroutines vs callbacks for Room access

| Approach | Pros | Cons |
|---|---|---|
| Suspend functions + coroutines | Standard modern Room pattern, Compose-friendly | Requires coroutine understanding |
| Callbacks (LiveData) | Older pattern, more examples online | Verbose, less Compose-friendly |
| RxJava | Functional reactive | Heavy dependency, overkill |

**Recommendation:** Suspend functions + coroutines. This is the standard modern Room pattern and will make Step 06 (UI) simpler with Compose. All DAO methods should be `suspend` functions.

---

### 4. Project namespace and package structure

| Option | Package Name |
|---|---|
| Feature-based (matches INSTRUCTIONS.md) | `com.eykon.memory` with sub-packages `data`, `ui`, `capture`, etc. |
| Flat | Everything in `com.eykon.memory` |

**Recommendation:** Feature-based, matching INSTRUCTIONS.md §2. Use `com.eykon.memory.data` for Room entities/DAO/database, `com.eykon.memory.ui` for Compose screens, `com.eykon.memory.capture` for text/voice input, `com.eykon.memory.ml` for LiteRT-LM and embedding wrappers.

---

### 5. Minimum SDK version

| SDK | Android Version | Compatibility | Notes |
|---|---|---|---|
| 31 (S) | Android 12 | Target for Gemma 4 / LiteRT-LM | Required for LiteRT-LM on-device inference and modern hardware buffers |

**Decision:** **API Level 31 (Android 12)**. Gemma 4 and the LiteRT-LM runtime require Android 12 (API 31)+ for native acceleration and model execution.
Compile SDK: 34 or 35. Target SDK: 34 or 35. Min SDK: 31.


---

## How to Implement

1. **Create Android project** in Android Studio:
   - Language: Kotlin, Build: Gradle (Kotlin DSL)
   - Minimum SDK: 26
   - Template: Empty Compose Activity

2. **Add dependencies** to `app/build.gradle.kts`:
   ```kotlin
   dependencies {
       // Room
       val roomVersion = "2.6.1"
       implementation("androidx.room:room-runtime:$roomVersion")
       implementation("androidx.room:room-ktx:$roomVersion")  // coroutine support
       ksp("androidx.room:room-compiler:$roomVersion")
       
       // Coroutines
       implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
       
       // JSON serialization for embedding TypeConverter
       implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.1")
       
       // Compose (should come with template)
       // ...standard Compose BOM dependencies...
       
       // Testing
       androidTestImplementation("androidx.room:room-testing:$roomVersion")
       androidTestImplementation("androidx.test.ext:junit:1.2.1")
   }
   ```

3. **Create `MemoryRecord.kt`** (Room @Entity):
   ```kotlin
   @Entity(tableName = "memories")
   data class MemoryRecord(
       @PrimaryKey(autoGenerate = true)
       val id: Int = 0,
       
       @ColumnInfo(name = "text")
       val text: String,
       
       @ColumnInfo(name = "embedding")
       val embedding: String,  // JSON-encoded List<Float>
       
       @ColumnInfo(name = "timestamp")
       val timestamp: String,  // ISO 8601
       
       @ColumnInfo(name = "source_type")
       val sourceType: String = "text",
       
       @ColumnInfo(name = "metadata")
       val metadata: String = "{}"  // JSON-encoded chunk metadata
   )
   ```

4. **Create `MemoryDao.kt`** (CRUD):
   ```kotlin
   @Dao
   interface MemoryDao {
       @Insert
       suspend fun insert(record: MemoryRecord): Long
       
       @Insert
       suspend fun insertAll(records: List<MemoryRecord>): List<Long>
       
       @Query("SELECT * FROM memories ORDER BY timestamp DESC")
       suspend fun getAll(): List<MemoryRecord>
       
       @Query("SELECT * FROM memories WHERE id = :id")
       suspend fun getById(id: Int): MemoryRecord?
       
       @Query("DELETE FROM memories WHERE id = :id")
       suspend fun deleteById(id: Int)
       
       @Query("SELECT COUNT(*) FROM memories")
       suspend fun count(): Int
       
       @Query("DELETE FROM memories")
       suspend fun deleteAll()
   }
   ```

5. **Create `MemoryDatabase.kt`**:
   ```kotlin
   @Database(entities = [MemoryRecord::class], version = 1)
   @TypeConverters(Converters::class)
   abstract class MemoryDatabase : RoomDatabase() {
       abstract fun memoryDao(): MemoryDao
   }
   ```

6. **Create `Converters.kt`** (JSON ↔ List<Float> TypeConverter):
   ```kotlin
   class Converters {
       @TypeConverter
       fun fromEmbeddingJson(json: String): List<Float> =
           Json.decodeFromString(json)
       
       @TypeConverter
       fun toEmbeddingJson(embedding: List<Float>): String =
           Json.encodeToString(embedding)
   }
   ```

7. **Wire up** in `MemoryApp.kt` (Application class) with lazy singleton:
   ```kotlin
   class MemoryApp : Application() {
       val database: MemoryDatabase by lazy {
           Room.databaseBuilder(this, MemoryDatabase::class.java, "memories.db")
               .build()
       }
   }
   ```

---

## Verification

### Automated (Instrumented Test)

```kotlin
// MemoryDaoTest.kt
@RunWith(AndroidJUnit4::class)
class MemoryDaoTest {
    private lateinit var db: MemoryDatabase
    private lateinit var dao: MemoryDao

    @Before
    fun setup() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            MemoryDatabase::class.java
        ).build()
        dao = db.memoryDao()
    }

    @After
    fun teardown() { db.close() }

    @Test
    fun insertAndRetrieve() = runBlocking {
        val record = MemoryRecord(
            text = "Dentist appointment on the 14th",
            embedding = Json.encodeToString(List(384) { 0.1f }),
            timestamp = "2026-09-07T12:00:00",
            sourceType = "text"
        )
        val id = dao.insert(record)
        val fetched = dao.getById(id.toInt())
        assertNotNull(fetched)
        assertEquals("Dentist appointment on the 14th", fetched!!.text)
        assertEquals(1, dao.count())
    }
}
```

### Manual (on real device or emulator)

```bash
# Run instrumented tests on connected device
./gradlew connectedAndroidTest

# Build and install debug APK
./gradlew installDebug

# Verify DB creation via adb
adb shell run-as com.eykon.memory ls databases/
# Should show: memories.db
```

---

## Research Notes

> _Leave your notes here as you research._

- [ ] Which JSON library for TypeConverter? (kotlinx.serialization / Gson / Moshi)
- [ ] Room version compatibility with target SDK?
- [ ] LiteRT-LM minimum Android API level?
- [ ] Does the project need KSP or KAPT for Room annotation processing?
- [ ] Any Room migration gotchas for future schema changes?

---

## Files Changed

- `app/build.gradle.kts` (Room, coroutines, kotlinx-serialization dependencies)
- `data/MemoryRecord.kt` (new — Room @Entity)
- `data/MemoryDao.kt` (new — CRUD interface)
- `data/MemoryDatabase.kt` (new — Room database)
- `data/Converters.kt` (new — JSON TypeConverter)
- `MemoryApp.kt` (new — Application class with DB singleton)
- `MainActivity.kt` (empty Compose shell)
- `MemoryDaoTest.kt` (new — instrumented test)
