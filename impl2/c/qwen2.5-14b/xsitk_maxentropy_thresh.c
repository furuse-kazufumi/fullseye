#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムのビン数を計算
    int bin_count = 64 + 192 * a;
    if (bin_count < 64) bin_count = 64;
    if (bin_count > 256) bin_count = 256;

    // ヒストグラムを初期化
    int* histogram = (int*)calloc(bin_count, sizeof(int));
    if (histogram == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // ヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int bin_index = (int)(in[y * w + x] * bin_count);
            if (bin_index >= bin_count) bin_index = bin_count - 1;
            histogram[bin_index]++;
        }
    }

    // 累積分布関数 (CDF) を計算
    int total_pixels = h * w;
    double* cdf = (double*)calloc(bin_count, sizeof(double));
    if (cdf == NULL) {
        free(histogram);
        return;
    }
    cdf[0] = histogram[0] / (double)total_pixels;
    for (int i = 1; i < bin_count; i++) {
        cdf[i] = cdf[i - 1] + histogram[i] / (double)total_pixels;
    }

    // 最大エントロピー閾値を計算
    double max_entropy = -1.0;
    int threshold = 0;
    for (int i = 0; i < bin_count; i++) {
        double entropy = 0.0;
        for (int j = 0; j < bin_count; j++) {
            double p = cdf[j] - (j > i ? cdf[j - 1] : 0);
            if (p > 0) {
                entropy -= p * log(p);
            }
        }
        if (entropy > max_entropy) {
            max_entropy = entropy;
            threshold = i;
        }
    }

    // 二値化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (in[y * w + x] * bin_count > threshold) ? 1.0 : 0.0;
        }
    }

    // メモリ解放
    free(histogram);
    free(cdf);
}
