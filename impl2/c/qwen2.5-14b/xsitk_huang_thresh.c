#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムのビン数を計算
    int bin_count = (int)(64 + (256 - 64) * a);
    if (bin_count < 64) bin_count = 64;
    if (bin_count > 256) bin_count = 256;

    // ヒストグラムの初期化
    double* histogram = (double*)malloc(bin_count * sizeof(double));
    memset(histogram, 0, bin_count * sizeof(double));

    // ヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int bin_index = (int)(in[y * w + x] * bin_count);
            if (bin_index >= bin_count) bin_index = bin_count - 1;
            histogram[bin_index]++;
        }
    }

    // ファジィエントロピーを計算
    double min_entropy = DBL_MAX;
    int threshold = 0;
    for (int t = 0; t < bin_count; t++) {
        double entropy = 0.0;
        for (int i = 0; i < t; i++) {
            double p = histogram[i] / (h * w);
            if (p > 0) entropy += p * log(p);
        }
        for (int i = t; i < bin_count; i++) {
            double p = histogram[i] / (h * w);
            if (p > 0) entropy += p * log(p);
        }
        if (entropy < min_entropy) {
            min_entropy = entropy;
            threshold = t;
        }
    }

    // 二値化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (in[y * w + x] < (threshold / (double)bin_count)) ? 0.0 : 1.0;
        }
    }

    // ヒストグラムのメモリを解放
    free(histogram);
}
