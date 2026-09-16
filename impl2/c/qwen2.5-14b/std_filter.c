#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * 8 + 3); // 3, 5, 7, 9 に近似
    int half_window = window_size / 2;

    // 出力画像の最大値を初期化
    double max_output = 0.0;

    // 出力画像の各ピクセルに対して計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 局所窓内のピクセルを処理
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓外のピクセルは無視
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    double value = in[ny * w + nx];
                    sum += value;
                    sum_sq += value * value;
                    count++;
                }
            }

            // 平均と分散を計算
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);

            // 標準偏差を計算
            double std_dev = sqrt(variance);

            // 出力画像の最大値を更新
            if (std_dev > max_output) {
                max_output = std_dev;
            }

            // 出力画像に標準偏差を格納
            out[y * w + x] = std_dev;
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_output;
    }
}
