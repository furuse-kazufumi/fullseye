#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int k = 3 + 2 * (int)(a * 3);
    int se_half = k / 2;

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // エラーチェック
    if (k % 2 == 0) {
        fprintf(stderr, "Structuring element size must be odd.\n");
        exit(EXIT_FAILURE);
    }

    // エラスティックな収縮と膨張を適用
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (!temp) {
        fprintf(stderr, "Memory allocation failed.\n");
        exit(EXIT_FAILURE);
    }

    // 収縮
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double min_val = in[y * w + x];
            for (int dy = -se_half; dy <= se_half; ++dy) {
                for (int dx = -se_half; dx <= se_half; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            temp[y * w + x] = min_val;
        }
    }

    // 膨張
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double max_val = temp[y * w + x];
            for (int dy = -se_half; dy <= se_half; ++dy) {
                for (int dx = -se_half; dx <= se_half; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, temp[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }

    free(temp);
}
