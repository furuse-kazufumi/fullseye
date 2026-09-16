#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Frei-Chen カーネル
    const double _FREI[2][3][3] = {
        {
            {-1.0, 0.0, 1.0},
            {-2.0, 0.0, 2.0},
            {-1.0, 0.0, 1.0}
        },
        {
            {1.0, 2.0, 1.0},
            {0.0, 0.0, 0.0},
            {-1.0, -2.0, -1.0}
        }
    };

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.5; // 初期値は 0.5 (0°)
        }
    }

    // 画像の各ピクセルに対して処理
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = 0.0, gy = 0.0;

            // カーネルを適用
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    double in_val = in[(y + ky) * w + (x + kx)];
                    gx += _FREI[0][ky + 1][kx + 1] * in_val;
                    gy += _FREI[1][ky + 1][kx + 1] * in_val;
                }
            }

            // arctan2 を使用して角度を計算
            out[y * w + x] = atan2(gy, gx) / (2 * M_PI) + 0.5; // [0, 1] に正規化
        }
    }
}
