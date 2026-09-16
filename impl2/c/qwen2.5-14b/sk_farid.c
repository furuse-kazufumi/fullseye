#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない
    (void)a;
    (void)b;

    // 5x5 の Farid カーネル
    const double kernel[5][5] = {
        { -1.0 / 16, -1.0 / 8, -1.0 / 16, 0, 1.0 / 16 },
        { -1.0 / 8, -1.0 / 4, -1.0 / 8, 0, 1.0 / 8 },
        { -1.0 / 16, -1.0 / 8, -1.0 / 16, 0, 1.0 / 16 },
        { 0, 0, 0, 0, 0 },
        { 1.0 / 16, 1.0 / 8, 1.0 / 16, 0, -1.0 / 16 }
    };

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 画像の各ピクセルに対してカーネルを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double gx = 0.0, gy = 0.0;

            // カーネルを適用
            for (int ky = 0; ky < 5; ++ky) {
                for (int kx = 0; kx < 5; ++kx) {
                    int iy = y + ky - 2;
                    int ix = x + kx - 2;

                    // 画像の境界外を処理するための補間
                    if (iy < 0 || iy >= h || ix < 0 || ix >= w) {
                        // 端のピクセルは境界値を用いる
                        if (iy < 0) iy = 0;
                        if (iy >= h) iy = h - 1;
                        if (ix < 0) ix = 0;
                        if (ix >= w) ix = w - 1;
                    }

                    double value = in[iy * w + ix];
                    gx += value * kernel[ky][kx];
                    gy += value * kernel[kx][ky];
                }
            }

            // 勾配の大きさを計算
            double magnitude = sqrt(gx * gx + gy * gy);
            out[y * w + x] = magnitude;

            // 最大値を更新
            if (magnitude > max_out) {
                max_out = magnitude;
            }
        }
    }

    // 出力を最大値で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
