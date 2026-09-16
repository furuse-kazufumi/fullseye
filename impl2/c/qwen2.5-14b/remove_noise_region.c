#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 圧縮後の画像の高さと幅を計算
    int h1 = h - 2 * (int)ceil(a);
    int w1 = w - 2 * (int)ceil(a);
    // 圧縮後の画像を確保
    double* in1 = (double*)malloc(h1 * w1 * sizeof(double));
    // 膨張後の画像を確保
    double* out1 = (double*)malloc(h * w * sizeof(double));

    // 入力画像を圧縮
    for (int y = (int)ceil(a); y < h - (int)ceil(a); y++) {
        for (int x = (int)ceil(a); x < w - (int)ceil(a); x++) {
            int sum = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (sqrt(dx * dx + dy * dy) <= a) {
                        sum += in[(y + dy) * w + (x + dx)] > 0.5;
                    }
                }
            }
            in1[(y - (int)ceil(a)) * w1 + (x - (int)ceil(a))] = sum > 0 ? 1.0 : 0.0;
        }
    }

    // 圧縮画像を膨張
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int sum = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int y1 = y + dy + (int)ceil(a);
                    int x1 = x + dx + (int)ceil(a);
                    if (y1 >= 0 && y1 < h1 && x1 >= 0 && x1 < w1) {
                        if (sqrt(dx * dx + dy * dy) <= a) {
                            sum += in1[y1 * w1 + x1] > 0.5;
                        }
                    }
                }
            }
            out[y * w + x] = sum > 0 ? 1.0 : 0.0;
        }
    }

    // メモリを解放
    free(in1);
    free(out1);
}
