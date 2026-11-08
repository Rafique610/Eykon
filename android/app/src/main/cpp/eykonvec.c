/*
 * EYKO-114 option 2: dot products straight from a memory-mapped vector file, with NEON.
 * Same arithmetic as VideoVectors.dot(): four running sums (lane j adds the elements i with i % 4 == j),
 * a separate multiply and add (no fused multiply-add; build with -ffp-contract=off), and the result
 * (s0 + s1) + (s2 + s3). So the scores are bit-identical to the heap path. Four rows are scored at once
 * so the CPU can overlap them; each row keeps its own sum order. Built by `task build-vector-native`.
 */
#include <arm_neon.h>
#include <jni.h>

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
