#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 平滑化の空間範囲 sigma_s を計算
    double sigma_s = 20 + a * 80;
    // 色差許容 sigma_r と陰影の濃さ shade_factor を計算
    double sigma_r = 0.05 + b * 0.15;
    double shade_factor = 0.02 + b * 0.06;

    // 平滑化とドッジ合成のための一時的な画像を確保
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    double* dodge = (double*)malloc(h * w * sizeof(double));

    // 平滑化処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double weight = exp(-(dx * dx + dy * dy) / (2 * sigma_s * sigma_s));
                        sum += in[ny * w + nx] * weight;
                        weight_sum += weight;
                    }
                }
            }
            smoothed[y * w + x] = sum / weight_sum;
        }
    }

    // ドッジ合成処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double diff = fabs(in[y * w + x] - smoothed[y * w + x]);
            double weight = exp(-diff * diff / (2 * sigma_r * sigma_r));
            dodge[y * w + x] = in[y * w + x] + (1 - in[y * w + x]) * (smoothed[y * w + x] - in[y * w + x]) * shade_factor * weight;
        }
    }

    // 出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = dodge[y * w + x];
        }
    }

    // 一時的な画像を解放
    free(smoothed);
    free(dodge);
}
