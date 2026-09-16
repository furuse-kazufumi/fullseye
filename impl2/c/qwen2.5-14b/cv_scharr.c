#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // 端の画素を重複させずに折り返す (BORDER_REFLECT_101)
    // これは、Scharr フィルタを適用する際に端の画素をどのように扱うかを定義します。
    // 画像の端の画素は、その画素の値を用いて反射的に補間されます。

    // Scharr フィルタの定義
    const double scharr_x[3][3] = {
        {-3, 0, 3},
        {-10, 0, 10},
        {-3, 0, 3}
    };
    const double scharr_y[3][3] = {
        {3, 10, 3},
        {0, 0, 0},
        {-3, -10, -3}
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各画素を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double gx = 0.0, gy = 0.0;

            // Scharr フィルタを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int y_idx = y + ky;
                    int x_idx = x + kx;
                    // 端の画素を重複させずに折り返す
                    if (y_idx < 0) y_idx = -y_idx - 1;
                    if (y_idx >= h) y_idx = 2 * h - y_idx - 2;
                    if (x_idx < 0) x_idx = -x_idx - 1;
                    if (x_idx >= w) x_idx = 2 * w - x_idx - 2;

                    double val = in[y_idx * w + x_idx];
                    gx += val * scharr_x[ky + 1][kx + 1];
                    gy += val * scharr_y[ky + 1][kx + 1];
                }
            }

            // 勾配強度を計算
            double edge_strength = fabs(gx) + fabs(gy);
            out[y * w + x] = edge_strength;

            // 出力画像の最大値を更新
            if (edge_strength > max_out) {
                max_out = edge_strength;
            }
        }
    }

    // 出力画像を最大値で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
