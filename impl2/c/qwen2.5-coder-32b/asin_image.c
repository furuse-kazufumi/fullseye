#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用のパラメータであるため、無視する。
    // 画像の各ピクセルに対して arcsin(x) / (π/2) を計算する。
    // 値域 [0, 1] を想定するが、範囲外の値が来ても落ちないように
    // clamp 処理を行う。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            // 値を [0, 1] の範囲に clamp
            if (pixel < 0.0) {
                pixel = 0.0;
            } else if (pixel > 1.0) {
                pixel = 1.0;
            }
            // arcsin を計算し、出力を [0, 1] に正規化
            out[y * w + x] = asin(pixel) / (M_PI / 2.0);
        }
    }
}
