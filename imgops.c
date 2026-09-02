/* imgevolve C runtime. stdlib + math only. difftest.py compiles + verifies it
 * against the Python backend whenever a C toolchain is available (gcc/clang on
 * PATH, or `python -m ziglang cc` — see algo_difftest.find_c_compiler). */
#include "imgops.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static int reflect(int i, int n) {           /* scipy 'reflect' (d c b a | a b c d) */
    if (n == 1) return 0;
    while (i < 0 || i >= n) {
        if (i < 0) i = -i - 1;
        if (i >= n) i = 2 * n - i - 1;
    }
    return i;
}

static float clampf(float x, float lo, float hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

void gaussian(float* buf, int w, int h, float sigma) {
    if (sigma <= 1e-6f) return;
    int r = (int)(4.0f * sigma + 0.5f);       /* scipy truncate=4.0 */
    if (r < 1) r = 1;
    int klen = 2 * r + 1;
    float* k = (float*)malloc(sizeof(float) * klen);
    float s = 0.0f;
    for (int i = -r; i <= r; i++) { k[i + r] = expf(-(float)(i * i) / (2.0f * sigma * sigma)); s += k[i + r]; }
    for (int i = 0; i < klen; i++) k[i] /= s;
    float* tmp = (float*)malloc(sizeof(float) * w * h);
    /* horizontal */
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i <= r; i++) acc += k[i + r] * buf[y * w + reflect(x + i, w)];
            tmp[y * w + x] = acc;
        }
    /* vertical */
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i <= r; i++) acc += k[i + r] * tmp[reflect(y + i, h) * w + x];
            buf[y * w + x] = acc;
        }
    free(tmp); free(k);
}

void box(float* buf, int w, int h, int k) {
    /* Mirrors scipy.ndimage.uniform_filter(size=k, origin=0): the window at x is
     * x-k/2 .. x-k/2+k-1, i.e. exactly k taps for ODD and EVEN k (-r..r for odd k,
     * -r..r-1 for even k). The old `-r..r` loop summed k+1 taps for an even k and
     * still divided by k (box(4) on a step edge peaked at 1.5625). */
    if (k < 1) return;
    int r = k / 2;
    int hi = k - r;                                /* exclusive upper offset */
    float* tmp = (float*)malloc(sizeof(float) * w * h);
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i < hi; i++) acc += buf[y * w + reflect(x + i, w)];
            tmp[y * w + x] = acc / (float)k;
        }
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i < hi; i++) acc += tmp[reflect(y + i, h) * w + x];
            buf[y * w + x] = acc / (float)k;
        }
    free(tmp);
}

void gamma_op(float* buf, int w, int h, float g) {
    for (int i = 0; i < w * h; i++) buf[i] = powf(clampf(buf[i], 0.0f, 1.0f), g);
}

void threshold(float* buf, int w, int h, float t) {
    for (int i = 0; i < w * h; i++) buf[i] = buf[i] > t ? 1.0f : 0.0f;
}

void invert(float* buf, int w, int h) {
    for (int i = 0; i < w * h; i++) buf[i] = 1.0f - clampf(buf[i], 0.0f, 1.0f);
}

void scale_clip(float* buf, int w, int h, float gain, float bias) {
    for (int i = 0; i < w * h; i++) buf[i] = clampf(gain * buf[i] + bias, 0.0f, 1.0f);
}

void sharpen(float* buf, int w, int h, float amount, float sigma) {
    /* Unsharp mask, clipped to [0,1] at the exit exactly like ops._unsharp: the
     * raw v + k*(v - blur) overshoots (measured [-0.15, 1.15]), and an unclipped
     * value fed to the NEXT stage diverged from the Python runtime (unsharp ->
     * gaussian max|C-py| 6.7e-2; unsharp -> threshold(1.0) flipped 512 px). */
    float* blur = (float*)malloc(sizeof(float) * w * h);
    memcpy(blur, buf, sizeof(float) * w * h);
    gaussian(blur, w, h, sigma);
    for (int i = 0; i < w * h; i++) buf[i] = clampf(buf[i] + amount * (buf[i] - blur[i]), 0.0f, 1.0f);
    free(blur);
}

void clamp01(float* buf, int w, int h) {
    /* The inter-stage clip ops._apply performs after every image/region stage.
     * codegen.py emits it after each stage so a future op that forgets its own
     * exit clip cannot leak an out-of-range value into the next stage. */
    for (int i = 0; i < w * h; i++) buf[i] = clampf(buf[i], 0.0f, 1.0f);
}

void sobel_mag(float* buf, int w, int h) {
    /* scipy sobel: smoothing [1,2,1] along the non-derivative axis, [-1,0,1] deriv. */
    float* gx = (float*)malloc(sizeof(float) * w * h);
    float* gy = (float*)malloc(sizeof(float) * w * h);
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float a = buf[reflect(y - 1, h) * w + reflect(x - 1, w)];
            float b = buf[reflect(y - 1, h) * w + x];
            float c = buf[reflect(y - 1, h) * w + reflect(x + 1, w)];
            float d = buf[y * w + reflect(x - 1, w)];
            float f = buf[y * w + reflect(x + 1, w)];
            float g = buf[reflect(y + 1, h) * w + reflect(x - 1, w)];
            float i2 = buf[reflect(y + 1, h) * w + x];
            float j = buf[reflect(y + 1, h) * w + reflect(x + 1, w)];
            gx[y * w + x] = (c + 2 * f + j) - (a + 2 * d + g);
            gy[y * w + x] = (g + 2 * i2 + j) - (a + 2 * b + c);
        }
    float mx = 0.0f;
    for (int i = 0; i < w * h; i++) { buf[i] = hypotf(gx[i], gy[i]); if (buf[i] > mx) mx = buf[i]; }
    if (mx > 1e-8f) for (int i = 0; i < w * h; i++) buf[i] /= mx;
    free(gx); free(gy);
}
