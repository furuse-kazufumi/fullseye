#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a はカットオフ率を表す。範囲は [0, 1]。
    // b は無視される。
    int cutoff = (int)(a * 10); // 0 から 10 の整数値に変換
    if (cutoff < 0) cutoff = 0;
    if (cutoff > 10) cutoff = 10;

    // ヒストグラムの計算
    int hist[256] = {0};
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int val = (int)(in[y * w + x] * 255.0);
            hist[val]++;
        }
    }

    // ヒストグラムの累積分布関数 (CDF) を計算
    int cdf[256] = {0};
    int total = h * w;
    int cdf_min = 256, cdf_max = 0;
    for (int i = 0; i < 256; i++) {
        cdf[i] = (i == 0) ? hist[i] : cdf[i - 1] + hist[i];
        if (cdf[i] > cutoff * total / 100) {
            if (i < cdf_min) cdf_min = i;
        }
        if (cdf[i] < (100 - cutoff) * total / 100) {
            if (i > cdf_max) cdf_max = i;
        }
    }

    // ヒストグラムの範囲を [cdf_min, cdf_max] に制限
    for (int i = 0; i < 256; i++) {
        if (i < cdf_min) cdf[i] = cdf[cdf_min];
        if (i > cdf_max) cdf[i] = cdf[cdf_max];
    }

    // CDF を使用して画像をリマッピング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int val = (int)(in[y * w + x] * 255.0);
            int mapped_val = (cdf[val] - cdf[cdf_min]) * 255 / (cdf[cdf_max] - cdf[cdf_min]);
            out[y * w + x] = mapped_val / 255.0;
        }
    }
}
