/* EYKO-108: minimal JNI over SQLite. sqlite-vec is registered for every new connection in JNI_OnLoad,
 * so nothing is loaded at run time (no load_extension, no dlopen of a second file). */
#include <jni.h>
#include <string.h>
#include <stdlib.h>
#include "sqlite3.h"
#include "sqlite-vec.h"

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)vm; (void)reserved;
    sqlite3_auto_extension((void (*)(void))sqlite3_vec_init);
    return JNI_VERSION_1_6;
}

#define FN(name) JNICALL Java_com_eykon_memory_spike_NativeSqlite_##name

JNIEXPORT jlong FN(nativeOpen)(JNIEnv *env, jclass c, jstring path) {
    const char *p = (*env)->GetStringUTFChars(env, path, NULL);
    sqlite3 *db = NULL;
    int rc = sqlite3_open(p, &db);
    (*env)->ReleaseStringUTFChars(env, path, p);
    if (rc != SQLITE_OK) { if (db) sqlite3_close(db); return 0; }
    return (jlong)(intptr_t)db;
}

JNIEXPORT void FN(nativeClose)(JNIEnv *env, jclass c, jlong db) { sqlite3_close((sqlite3 *)(intptr_t)db); }

JNIEXPORT jstring FN(nativeErrmsg)(JNIEnv *env, jclass c, jlong db) {
    return (*env)->NewStringUTF(env, sqlite3_errmsg((sqlite3 *)(intptr_t)db));
}

/* Runs one or more statements; returns null on success, else the error message. */
JNIEXPORT jstring FN(nativeExec)(JNIEnv *env, jclass c, jlong db, jstring sql) {
    const char *s = (*env)->GetStringUTFChars(env, sql, NULL);
    char *err = NULL;
    int rc = sqlite3_exec((sqlite3 *)(intptr_t)db, s, NULL, NULL, &err);
    (*env)->ReleaseStringUTFChars(env, sql, s);
    if (rc == SQLITE_OK) return NULL;
    jstring m = (*env)->NewStringUTF(env, err ? err : "error");
    sqlite3_free(err);
    return m;
}

JNIEXPORT jlong FN(nativePrepare)(JNIEnv *env, jclass c, jlong db, jstring sql) {
    const char *s = (*env)->GetStringUTFChars(env, sql, NULL);
    sqlite3_stmt *st = NULL;
    int rc = sqlite3_prepare_v2((sqlite3 *)(intptr_t)db, s, -1, &st, NULL);
    (*env)->ReleaseStringUTFChars(env, sql, s);
    return rc == SQLITE_OK ? (jlong)(intptr_t)st : 0;
}

JNIEXPORT jint FN(nativeStep)(JNIEnv *env, jclass c, jlong st) { return sqlite3_step((sqlite3_stmt *)(intptr_t)st); }
JNIEXPORT jint FN(nativeReset)(JNIEnv *env, jclass c, jlong st) { return sqlite3_reset((sqlite3_stmt *)(intptr_t)st); }
JNIEXPORT void FN(nativeFinalize)(JNIEnv *env, jclass c, jlong st) { sqlite3_finalize((sqlite3_stmt *)(intptr_t)st); }

JNIEXPORT jint FN(nativeBindLong)(JNIEnv *env, jclass c, jlong st, jint i, jlong v) { return sqlite3_bind_int64((sqlite3_stmt *)(intptr_t)st, i, v); }
JNIEXPORT jint FN(nativeBindDouble)(JNIEnv *env, jclass c, jlong st, jint i, jdouble v) { return sqlite3_bind_double((sqlite3_stmt *)(intptr_t)st, i, v); }

JNIEXPORT jint FN(nativeBindBlob)(JNIEnv *env, jclass c, jlong st, jint i, jbyteArray b) {
    jsize n = (*env)->GetArrayLength(env, b);
    jbyte *p = (*env)->GetByteArrayElements(env, b, NULL);
    int rc = sqlite3_bind_blob((sqlite3_stmt *)(intptr_t)st, i, p, n, SQLITE_TRANSIENT);
    (*env)->ReleaseByteArrayElements(env, b, p, JNI_ABORT);
    return rc;
}

JNIEXPORT jint FN(nativeBindText)(JNIEnv *env, jclass c, jlong st, jint i, jstring t) {
    const char *s = (*env)->GetStringUTFChars(env, t, NULL);
    int rc = sqlite3_bind_text((sqlite3_stmt *)(intptr_t)st, i, s, -1, SQLITE_TRANSIENT);
    (*env)->ReleaseStringUTFChars(env, t, s);
    return rc;
}

JNIEXPORT jlong FN(nativeColumnLong)(JNIEnv *env, jclass c, jlong st, jint i) { return sqlite3_column_int64((sqlite3_stmt *)(intptr_t)st, i); }
JNIEXPORT jdouble FN(nativeColumnDouble)(JNIEnv *env, jclass c, jlong st, jint i) { return sqlite3_column_double((sqlite3_stmt *)(intptr_t)st, i); }

JNIEXPORT jstring FN(nativeColumnText)(JNIEnv *env, jclass c, jlong st, jint i) {
    const unsigned char *t = sqlite3_column_text((sqlite3_stmt *)(intptr_t)st, i);
    return t ? (*env)->NewStringUTF(env, (const char *)t) : NULL;
}

JNIEXPORT jbyteArray FN(nativeColumnBlob)(JNIEnv *env, jclass c, jlong st, jint i) {
    const void *p = sqlite3_column_blob((sqlite3_stmt *)(intptr_t)st, i);
    int n = sqlite3_column_bytes((sqlite3_stmt *)(intptr_t)st, i);
    if (!p) return NULL;
    jbyteArray a = (*env)->NewByteArray(env, n);
    (*env)->SetByteArrayRegion(env, a, 0, n, (const jbyte *)p);
    return a;
}

/* Memory pressure for the EYKO-108 background test: takes [mb] more megabytes of real RAM (touched), returns the total taken. */
#define MAX_HOG 8192
static void *hog[MAX_HOG];
static int hogCount = 0;

JNIEXPORT jint FN(nativeHogStep)(JNIEnv *env, jclass c, jint mb) {
    for (int i = 0; i < mb && hogCount < MAX_HOG; i++) {
        void *p = malloc(1 << 20);
        if (!p) break;
        memset(p, 1, 1 << 20);
        hog[hogCount++] = p;
    }
    return hogCount;
}

JNIEXPORT void FN(nativeHogFree)(JNIEnv *env, jclass c) {
    while (hogCount > 0) free(hog[--hogCount]);
}
