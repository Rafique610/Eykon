/*
 * EYKO-114 option 2: dot products straight from a memory-mapped vector file, with NEON.
 * Same arithmetic as VideoVectors.dot(): four running sums (lane j adds the elements i with i % 4 == j),
 * a separate multiply and add (no fused multiply-add; build with -ffp-contract=off), and the result
 * (s0 + s1) + (s2 + s3). So the scores are bit-identical to the heap path. Four rows are scored at once
 * so the CPU can overlap them; each row keeps its own sum order. Built by `task build-vector-native`.
 */
#include <arm_neon.h>
#include <jni.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>

static inline float lanes(float32x4_t a) {
    return (vgetq_lane_f32(a, 0) + vgetq_lane_f32(a, 1)) + (vgetq_lane_f32(a, 2) + vgetq_lane_f32(a, 3));
}

JNIEXPORT void JNICALL Java_com_eykon_memory_video_VectorNative_scoreF32(
    JNIEnv *env, jclass cls, jobject buffer, jint rows, jint size, jfloatArray query, jfloatArray out, jint offset) {
    (void)cls;
    const float *base = (const float *)(*env)->GetDirectBufferAddress(env, buffer);
    if (base == NULL || size % 4 != 0) {
        (*env)->ThrowNew(env, (*env)->FindClass(env, "java/lang/IllegalArgumentException"), "need a direct buffer and size % 4 == 0");
        return;
    }
    float *q = (*env)->GetPrimitiveArrayCritical(env, query, NULL);
    float *o = (*env)->GetPrimitiveArrayCritical(env, out, NULL);
    jint r = 0;
    for (; r + 4 <= rows; r += 4) {
        const float *v0 = base + (size_t)r * size, *v1 = v0 + size, *v2 = v1 + size, *v3 = v2 + size;
        float32x4_t a0 = vdupq_n_f32(0), a1 = a0, a2 = a0, a3 = a0;
        for (jint i = 0; i < size; i += 4) {
            float32x4_t qi = vld1q_f32(q + i);
            a0 = vaddq_f32(a0, vmulq_f32(vld1q_f32(v0 + i), qi));
            a1 = vaddq_f32(a1, vmulq_f32(vld1q_f32(v1 + i), qi));
            a2 = vaddq_f32(a2, vmulq_f32(vld1q_f32(v2 + i), qi));
            a3 = vaddq_f32(a3, vmulq_f32(vld1q_f32(v3 + i), qi));
        }
        o[offset + r] = lanes(a0);
        o[offset + r + 1] = lanes(a1);
        o[offset + r + 2] = lanes(a2);
        o[offset + r + 3] = lanes(a3);
    }
    for (; r < rows; r++) {
        const float *v = base + (size_t)r * size;
        float32x4_t a = vdupq_n_f32(0);
        for (jint i = 0; i < size; i += 4) a = vaddq_f32(a, vmulq_f32(vld1q_f32(v + i), vld1q_f32(q + i)));
        o[offset + r] = lanes(a);
    }
    (*env)->ReleasePrimitiveArrayCritical(env, out, o, 0);
    (*env)->ReleasePrimitiveArrayCritical(env, query, q, JNI_ABORT);
}

/*
 * Hypothesis 4 (decision re-check, 26 Nov): hand a mapped chunk's pages back to the system when the app's screen is hidden.
 * The file is mapped read-only and shared, so MADV_DONTNEED only drops this process's copy of the pages: nothing is lost,
 * the next search reads them again from the page cache (or the file). Without it the pages stay counted in the process's
 * PSS (about 230 MB for 3 tables x 100k), which is where the Infinix killed it in the background (EYKO-116).
 * Only whole pages inside the buffer are released. Returns the bytes released, or -1 if madvise failed.
 */
JNIEXPORT jlong JNICALL Java_com_eykon_memory_video_VectorNative_release(JNIEnv *env, jclass cls, jobject buffer) {
    (void)cls;
    uint8_t *base = (uint8_t *)(*env)->GetDirectBufferAddress(env, buffer);
    jlong length = (*env)->GetDirectBufferCapacity(env, buffer);
    if (base == NULL || length <= 0) return 0;
    uintptr_t page = (uintptr_t)sysconf(_SC_PAGESIZE);
    uintptr_t start = ((uintptr_t)base + page - 1) & ~(page - 1);
    uintptr_t end = ((uintptr_t)base + (uintptr_t)length) & ~(page - 1);
    if (end <= start) return 0;
    return madvise((void *)start, end - start, MADV_DONTNEED) == 0 ? (jlong)(end - start) : -1;
}

/*
 * Hypotheses 2 + 3 (decision re-check, 26 Nov): the quick pass of "int8 first, exact float32 second". Each row is int8 codes
 * with one float scale per row; the phrase is int8 codes with one scale. out[offset + r] = scale[r] * qscale * sum(code * q).
 * Integer sums are exact, so the order of adding does not matter here. Measured against scoreF32 on the phone before any
 * search uses it (ModelAccelerator / Int8PassTest).
 */
JNIEXPORT void JNICALL Java_com_eykon_memory_video_VectorNative_scoreI8(
    JNIEnv *env, jclass cls, jobject buffer, jint rows, jint size, jfloatArray scales, jbyteArray query, jfloat qscale,
    jfloatArray out, jint offset) {
    (void)cls;
    const int8_t *base = (const int8_t *)(*env)->GetDirectBufferAddress(env, buffer);
    if (base == NULL || size % 16 != 0) {
        (*env)->ThrowNew(env, (*env)->FindClass(env, "java/lang/IllegalArgumentException"), "need a direct buffer and size % 16 == 0");
        return;
    }
    jbyte *q = (*env)->GetPrimitiveArrayCritical(env, query, NULL);
    float *s = (*env)->GetPrimitiveArrayCritical(env, scales, NULL);
    float *o = (*env)->GetPrimitiveArrayCritical(env, out, NULL);
    for (jint r = 0; r < rows; r++) {
        const int8_t *v = base + (size_t)r * size;
        int32x4_t acc = vdupq_n_s32(0);
        for (jint i = 0; i < size; i += 16) {
            int8x16_t a = vld1q_s8(v + i), b = vld1q_s8((const int8_t *)q + i);
            int16x8_t lo = vmull_s8(vget_low_s8(a), vget_low_s8(b));
            int16x8_t hi = vmull_s8(vget_high_s8(a), vget_high_s8(b));
            acc = vpadalq_s16(acc, lo);
            acc = vpadalq_s16(acc, hi);
        }
        o[offset + r] = s[r] * qscale * (float)vaddvq_s32(acc);
    }
    (*env)->ReleasePrimitiveArrayCritical(env, out, o, 0);
    (*env)->ReleasePrimitiveArrayCritical(env, scales, s, JNI_ABORT);
    (*env)->ReleasePrimitiveArrayCritical(env, query, q, JNI_ABORT);
}
