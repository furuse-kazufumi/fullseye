#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3 + (int)(2 * a); // a は [0, 1] の範囲で、窓サイズは 3/5/7/9 に変化
    int half_window = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 非極大値抑制
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            double threshold = 0.3 + 0.4 * b; // b は [0, 1] の範囲で、閾値は動的に変化

            // 窓内の最大値を求める
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 窓内の境界外を無視
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;

                    if (in[ny * w + nx] > max_val) {
                        max_val = in[ny * w + nx];
                    }
                }
            }

            // 窓内の最大値と一致し、かつ閾値を超える場合、前景として残す
            if (fabs(in[y * w + x] - max_val) < 1e-6 && in[y * w + x] > threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
