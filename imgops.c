/* imgevolve C runtime. stdlib + math only. Uncompiled in this environment
 * (no C toolchain); difftest.py compiles + verifies it against the Python
 * backend when a compiler is available. */
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
    int r = k / 2;
    float* tmp = (float*)malloc(sizeof(float) * w * h);
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i <= r; i++) acc += buf[y * w + reflect(x + i, w)];
            tmp[y * w + x] = acc / (float)k;
        }
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            float acc = 0.0f;
            for (int i = -r; i <= r; i++) acc += tmp[reflect(y + i, h) * w + x];
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

void sharpen(float* buf, int w, int h, float amount, float sigma) {
    float* blur = (float*)malloc(sizeof(float) * w * h);
    memcpy(blur, buf, sizeof(float) * w * h);
    gaussian(blur, w, h, sigma);
    for (int i = 0; i < w * h; i++) buf[i] = buf[i] + amount * (buf[i] - blur[i]);
    free(blur);
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
