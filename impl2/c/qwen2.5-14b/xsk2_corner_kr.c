#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。仕様書に従い無視する。

    // 出力画像のサイズは入力と同じ。
    int size = h * w;

    // 出力画像を初期化。Kitchen-Rosenfeld コーナー検出は NaN を 0 に置き換える。
    memset(out, 0, size * sizeof(double));

    // エッジ検出のためのマスク。Kitchen-Rosenfeld の場合、これは Sobel オペレータに相当する。
    const double mask_x[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    const double mask_y[3][3] = {
        {-1, -2, -1},
        {0, 0, 0},
        {1, 2, 1}
    };

    // 画像の各ピクセルに対して処理を行う。
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = 0.0, gy = 0.0;

            // エッジ検出のためのマスクを適用する。
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int idx = (y + ky) * w + (x + kx);
                    gx += mask_x[ky + 1][kx + 1] * in[idx];
                    gy += mask_y[ky + 1][kx + 1] * in[idx];
                }
            }

            // Kitchen-Rosenfeld のコーナー応答を計算する。
            double response = fabs(gx) * fabs(gy) - (0.04 * gx * gx + gy * gy);
            if (response < 0) {
                response = 0; // 負の応答は 0 に置き換える。
            }

            // 出力画像に応答を書き込む。
            int out_idx = y * w + x;
            out[out_idx] = response;
        }
    }
}
