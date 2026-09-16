#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    unsigned long hist[256];
    unsigned long total = 0;
    unsigned long background_count = 0;
    double total_sum = 0.0;
    double background_sum = 0.0;
    double best_variance = -1.0;
    int threshold_bin = 0;
    int i;
    int y;
    int x;

    (void)a;
    (void)b;

    memset(hist, 0, sizeof(hist));

    /*
     * 仕様で未規定の選択:
     * - Otsu 法には 256 ビンのヒストグラムを用いる。
     * - 有限な範囲外入力は [0,1] にクランプする。
     * - NaN は 0.0、正の無限大は 1.0、負の無限大は 0.0 として扱う。
     * - 最大のクラス間分散が複数ある場合は最小のしきい値を選ぶ。
     * - しきい値ビンより大きい画素を領域 (1.0) とする。
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t p = (size_t)y * (size_t)w + (size_t)x;
            double v = in[p];
            int bin;

            if (isnan(v) || v <= 0.0) {
                bin = 0;
            } else if (!isfinite(v) || v >= 1.0) {
                bin = 255;
            } else {
                bin = (int)floor(v * 255.0);
            }

            ++hist[bin];
            ++total;
            total_sum += (double)bin;
        }
    }

    for (i = 0; i < 256; ++i) {
        unsigned long foreground_count;
        double foreground_sum;
        double background_mean;
        double foreground_mean;
        double difference;
        double variance;

        background_count += hist[i];
        background_sum += (double)i * (double)hist[i];
        foreground_count = total - background_count;

        if (background_count == 0)
            continue;
        if (foreground_count == 0)
            break;

        foreground_sum = total_sum - background_sum;
        background_mean = background_sum / (double)background_count;
        foreground_mean = foreground_sum / (double)foreground_count;
        difference = background_mean - foreground_mean;
        variance = (double)background_count *
                   (double)foreground_count *
                   difference * difference;

        if (variance > best_variance) {
            best_variance = variance;
            threshold_bin = i;
        }
    }

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t p = (size_t)y * (size_t)w + (size_t)x;
            double v = in[p];
            int bin;

            if (isnan(v) || v <= 0.0) {
                bin = 0;
            } else if (!isfinite(v) || v >= 1.0) {
                bin = 255;
            } else {
                bin = (int)floor(v * 255.0);
            }

            out[p] = (bin > threshold_bin) ? 1.0 : 0.0;
        }
    }
}
