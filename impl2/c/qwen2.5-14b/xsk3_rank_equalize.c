#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円盤近傍の半径を計算
    int radius = 2 + (int)(a * 8);
    int disk_size = 2 * radius + 1;

    // ヒストグラムの初期化
    int hist_size = 256;
    int* hist = (int*)calloc(hist_size, sizeof(int));
    double* cdf = (double*)calloc(hist_size, sizeof(double));

    // ヒストグラムの計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int value = (int)(in[y * w + x] * 255);
            hist[value]++;
        }
    }

    // 累積分布関数 (CDF) の計算
    double cdf_sum = 0;
    for (int i = 0; i < hist_size; ++i) {
        cdf_sum += hist[i];
        cdf[i] = cdf_sum;
    }

    // CDF を正規化
    for (int i = 0; i < hist_size; ++i) {
        cdf[i] = cdf[i] / (h * w);
    }

    // 出力画像の生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int value = (int)(in[y * w + x] * 255);
            double cdf_value = cdf[value];
            double normalized_value = cdf_value * 255;
            out[y * w + x] = normalized_value / 255.0;
        }
    }

    // メモリの解放
    free(hist);
    free(cdf);
}
