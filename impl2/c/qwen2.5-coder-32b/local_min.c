#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(2 * a * fmin(h, w)) + 1;
    int half_window = window_size / 2;

    // 画像の端をどう扱うか: 境界外の画素は無視する (zero-padding と見なす)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            int is_local_min = 1;

            // 窓内の最小値を求める
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 境界外の画素は無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] < min_val) {
                            min_val = in[ny * w + nx];
                        }
                    }
                }
            }

            // 窓内の最小値であるか確認
            if (in[y * w + x] != min_val) {
                is_local_min = 0;
            }

            // 輝度の上限しきい値を満たすか確認
            if (in[y * w + x] >= 0.7 - 0.4 * b) {
                is_local_min = 0;
            }

            // 出力設定
            out[y * w + x] = is_local_min ? 1.0 : 0.0;
        }
    }
}
