#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int window_size = (int)(a * 3.0); // a が [0,1] の範囲なので、窓サイズは [0,3] になる。ここでは 0 は無意味なので 1 から 3 に調整。
    if (window_size < 1) window_size = 1; // 窓サイズが 0 の場合は 1 に設定。
    int half_window = window_size / 2;

    double threshold = 0.3 + 0.4 * b; // 閾値の計算。

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double center_value = in[y * w + x];
            int is_local_max = 1;

            // 窓内の最大値を検出
            for (int wy = -half_window; wy <= half_window; wy++) {
                for (int wx = -half_window; wx <= half_window; wx++) {
                    int ny = y + wy;
                    int nx = x + wx;

                    // 境界外アクセスを防ぐ
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] > center_value) {
                            is_local_max = 0;
                            break;
                        }
                    }
                }
                if (!is_local_max) break;
            }

            // 閾値を満たすか確認
            if (is_local_max && center_value > threshold) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
