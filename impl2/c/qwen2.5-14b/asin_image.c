#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用パラメータであるため、無視する。
    // 出力画像の各ピクセルに対して arcsin(x) / (π/2) を適用する。
    // 入力画像のピクセル値が [0, 1] の範囲外の場合、その値を [0, 1] の範囲にクリップする。
    // これは仕様書で明示的に定義されていないが、一般的な画像処理の慣例に基づく。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // クリッピング
            if (value < 0.0) {
                value = 0.0;
            } else if (value > 1.0) {
                value = 1.0;
            }
            // arcsin(x) / (π/2) の計算
            out[idx] = asin(value) / M_PI_2;
        }
    }
}
