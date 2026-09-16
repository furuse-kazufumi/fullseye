#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int max_iterations = 9;
    const int stencil_radius = 1 + (int)(b * 2);
    const double time_step = 0.0625;
    const int stencil_size = (2 * stencil_radius + 1) * (2 * stencil_radius + 1);

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 曲率流平滑化と最小/最大値に基づく平滑化
    int iterations = (int)(a * max_iterations);
    for (int i = 0; i < iterations; ++i) {
        double stencil[stencil_size];
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                // ステンシルの計算
                int stencil_index = 0;
                for (int dy = -stencil_radius; dy <= stencil_radius; ++dy) {
                    for (int dx = -stencil_radius; dx <= stencil_radius; ++dx) {
                        int sy = y + dy;
                        int sx = x + dx;
                        if (sy >= 0 && sy < h && sx >= 0 && sx < w) {
                            stencil[stencil_index++] = in[sy * w + sx];
                        } else {
                            stencil[stencil_index++] = out[y * w + x]; // ボーダー処理: 周囲のピクセルをコピー
                        }
                    }
                }

                // 曲率流の計算
                double curvature = 0.0;
                for (int j = 0; j < stencil_size; ++j) {
                    curvature += fabs(stencil[j] - out[y * w + x]);
                }
                curvature /= stencil_size;

                // 最小/最大値に基づく平滑化
                double min_val = stencil[0];
                double max_val = stencil[0];
                for (int j = 1; j < stencil_size; ++j) {
                    if (stencil[j] < min_val) min_val = stencil[j];
                    if (stencil[j] > max_val) max_val = stencil[j];
                }

                // 出力の更新
                double new_val = out[y * w + x] + time_step * (curvature - (out[y * w + x] - min_val) * (out[y * w + x] - max_val));
                new_val = fmax(0.0, fmin(1.0, new_val)); // [0,1] にクリップ
                out[y * w + x] = new_val;
            }
        }
    }
}
