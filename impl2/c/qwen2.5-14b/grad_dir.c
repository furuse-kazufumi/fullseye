#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。仕様書に従い無視する。

    // 画像の端を処理する際、境界外のピクセルは近傍のピクセル値を用いる。
    // ここでは、境界外のピクセルを近傍のピクセル値で埋める。

    // Sobel オペレータのマスク
    const double sobel_x[3][3] = {{1, 0, -1}, {2, 0, -2}, {1, 0, -1}};
    const double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // エッジ検出
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double Gx = 0.0, Gy = 0.0;

            // Sobel オペレータを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    Gx += in[(y + ky) * w + (x + kx)] * sobel_x[ky + 1][kx + 1];
                    Gy += in[(y + ky) * w + (x + kx)] * sobel_y[ky + 1][kx + 1];
                }
            }

            // 勾配方向を計算
            double angle = atan2(Gy, Gx);
            out[y * w + x] = (angle + M_PI) / (2 * M_PI); // [0, 1] に正規化
        }
    }
}
