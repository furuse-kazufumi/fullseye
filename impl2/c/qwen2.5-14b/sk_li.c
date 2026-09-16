#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない

    // ヒストグラムの最大値
    const int hist_size = 256;
    int* hist = (int*)calloc(hist_size, sizeof(int));
    if (hist == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // ヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int value = (int)(in[y * w + x] * hist_size);
            if (value < 0) value = 0;
            if (value >= hist_size) value = hist_size - 1;
            hist[value]++;
        }
    }

    // しきい値を求める
    double threshold = 0.0;
    double min_entropy = DBL_MAX;
    for (int t = 1; t < hist_size - 1; t++) {
        double entropy = 0.0;
        int total = h * w;
        int total1 = 0;
        int total2 = 0;
        for (int i = 0; i < t; i++) {
            total1 += hist[i];
        }
        for (int i = t; i < hist_size; i++) {
            total2 += hist[i];
        }
        if (total1 > 0 && total2 > 0) {
            entropy += (-total1 / (double)total) * log(total1 / (double)total);
            entropy += (-total2 / (double)total) * log(total2 / (double)total);
        }
        if (entropy < min_entropy) {
            min_entropy = entropy;
            threshold = t / (double)(hist_size - 1);
        }
    }

    // 二値化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (in[y * w + x] < threshold) ? 0.0 : 1.0;
        }
    }

    // ヒストグラムのメモリを解放
    free(hist);
}
