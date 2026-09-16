#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は使用しないパラメータであるため、無視する。

    // 画像の最大値と最小値を求める
    double max_val = -INFINITY;
    double min_val = INFINITY;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            if (val > max_val) max_val = val;
            if (val < min_val) min_val = val;
        }
    }

    // 画像の値域を 256 ビンに分割する
    const int num_bins = 256;
    double* histogram = (double*)malloc(num_bins * sizeof(double));
    memset(histogram, 0, num_bins * sizeof(double));

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            int bin = (val - min_val) / (max_val - min_val) * (num_bins - 1);
            if (bin < 0) bin = 0;
            if (bin >= num_bins) bin = num_bins - 1;
            histogram[bin]++;
        }
    }

    // Otsu's method を適用する
    double total = h * w;
    double sum = 0.0;
    for (int i = 0; i < num_bins; ++i) {
        sum += i * histogram[i];
    }
    double w1 = 0.0;
    double m1 = 0.0;
    double max_var = 0.0;
    int threshold = 0;
    for (int i = 0; i < num_bins; ++i) {
        w1 += histogram[i];
        if (w1 == 0) continue;
        double w2 = total - w1;
        if (w2 == 0) break;
        m1 += i * histogram[i];
        double m2 = sum - m1;
        double var_between = w1 * w2 * pow((m1 / w1 - m2 / w2), 2);
        if (var_between > max_var) {
            max_var = var_between;
            threshold = i;
        }
    }

    // しきい値を用いて出力画像を生成する
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            int bin = (val - min_val) / (max_val - min_val) * (num_bins - 1);
            if (bin < 0) bin = 0;
            if (bin >= num_bins) bin = num_bins - 1;
            out[y * w + x] = (bin > threshold) ? 1.0 : 0.0;
        }
    }

    free(histogram);
}
