#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Frei-Chen エッジ検出カーネル
    const double kernel_x[3][3] = {
        {-1, 0, 1},
        {-sqrt(2), 0, sqrt(2)},
        {-1, 0, 1}
    };
    const double kernel_y[3][3] = {
        {-1, -sqrt(2), -1},
        {0, 0, 0},
        {1, sqrt(2), 1}
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各画素を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double gx = 0.0, gy = 0.0;

            // カーネルを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int iy = y + ky;
                    int ix = x + kx;
                    // 端の処理: 入力画像の端を重複させて折り返す
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = h - (iy - h + 1);
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = w - (ix - w + 1);

                    gx += kernel_x[ky + 1][kx + 1] * in[iy * w + ix];
                    gy += kernel_y[ky + 1][kx + 1] * in[iy * w + ix];
                }
            }

            // エッジ強度を計算
            double edge_strength = hypot(gx, gy);
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
