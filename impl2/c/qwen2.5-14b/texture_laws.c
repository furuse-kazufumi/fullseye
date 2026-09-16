#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は窓サイズを決定する。0.25, 0.49, 0.75 で切り替わる。
    int window_size = (a < 0.25) ? 3 : (a < 0.49) ? 5 : (a < 0.75) ? 7 : 9;
    int half_window = window_size / 2;

    // 出力を正規化するための最大値を計算する。
    double max_value = 0.0;

    // 画像の各ピクセルに対して処理を行う。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            // 窓内のピクセルを処理する。
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓外のピクセルは無視する。
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    double pixel = in[ny * w + nx];
                    sum += pixel;
                    sum_sq += pixel * pixel;
                    count++;
                }
            }

            // 局所分散を計算する。
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            out[y * w + x] = variance;

            // 正規化用の最大値を更新する。
            if (out[y * w + x] > max_value) {
                max_value = out[y * w + x];
            }
        }
    }

    // 出力を最大値で正規化する。
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_value;
    }
}
