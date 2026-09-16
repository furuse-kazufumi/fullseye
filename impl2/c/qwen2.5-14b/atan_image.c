#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用。仕様書に従い、これらのパラメータは無視する。

    // 出力画像の各ピクセルに対して atan_image 関数を適用する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double input = in[idx];
            // atan_image の定義に従い、入力画像の各ピクセルに対して arctan(x) / (π/2) を計算する。
            out[idx] = atan(input) / M_PI;
            out[idx] *= 2; // 正規化
        }
    }
}
