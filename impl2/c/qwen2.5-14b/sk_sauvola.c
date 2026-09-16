#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 2 * (int)(a * 6) + 3;
    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++;
    }

    // 辺のパディング
    int pad = window_size / 2;
    int padded_h = h + 2 * pad;
    int padded_w = w + 2 * pad;

    // パディングされた画像の作成
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + pad) * padded_w + (x + pad)] = in[y * w + x];
        }
    }
    // パディングの境界を0で埋める
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < pad; x++) {
            padded_in[(y + pad) * padded_w + x] = 0;
            padded_in[(y + pad) * padded_w + (x + pad + w)] = 0;
        }
    }
    for (int x = 0; x < padded_w; x++) {
        padded_in[x] = 0;
        padded_in[(padded_h - 1) * padded_w + x] = 0;
    }

    // 局所的な平均と標準偏差の計算
    double* local_mean = (double*)malloc(h * w * sizeof(double));
    double* local_stddev = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0;
            double sum_sq = 0;
            for (int dy = -pad; dy <= pad; dy++) {
                for (int dx = -pad; dx <= pad; dx++) {
                    int py = y + dy + pad;
                    int px = x + dx + pad;
                    double val = padded_in[py * padded_w + px];
                    sum += val;
                    sum_sq += val * val;
                }
            }
            double mean = sum / ((window_size * window_size));
            double stddev = sqrt((sum_sq / (window_size * window_size)) - (mean * mean));
            local_mean[y * w + x] = mean;
            local_stddev[y * w + x] = stddev;
        }
    }

    // しきい値の計算と二値化
    double k = 0.2; // Sauvola のパラメータ k
    double r = 128; // Sauvola のパラメータ r
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double mean = local_mean[y * w + x];
            double stddev = local_stddev[y * w + x];
            double threshold = mean * (1 + k * ((stddev / r) - 1));
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // メモリの解放
    free(padded_in);
    free(local_mean);
    free(local_stddev);
}
