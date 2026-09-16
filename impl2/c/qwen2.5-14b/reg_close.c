#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は無視する
    int iterations = (int)round(a * 4); // 0.1 から 0.9 までで 1 から 4 までの整数に変換
    if (iterations < 1) iterations = 1; // 最小 1 回の反復

    // 出力画像を入力画像と同じにする
    memcpy(out, in, h * w * sizeof(double));

    // 膨張処理
    for (int i = 0; i < iterations; i++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                temp[y * w + x] = 0.0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            temp[y * w + x] = fmax(temp[y * w + x], in[ny * w + nx]);
                        }
                    }
                }
            }
        }
        memcpy(out, temp, h * w * sizeof(double));
        free(temp);
    }

    // 侵食処理
    for (int i = 0; i < iterations; i++) {
        double* temp = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                temp[y * w + x] = 1.0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            temp[y * w + x] = fmin(temp[y * w + x], out[ny * w + nx]);
                        }
                    }
                }
            }
        }
        memcpy(out, temp, h * w * sizeof(double));
        free(temp);
    }
}
