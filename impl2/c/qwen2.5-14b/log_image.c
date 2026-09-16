#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用。これらのパラメータは無視する。
    // 出力は入力画像の各ピクセルに対して log1p(x) / log(2) を適用する。
    // 入力の範囲は [0,1] だが、範囲外の値も処理可能とする。
    // 範囲外の値に対しては、入力値をそのまま出力する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double input = in[idx];
            if (input >= 0.0 && input <= 1.0) {
                out[idx] = log1p(input) / log(2.0);
            } else {
                // 範囲外の値に対しては入力値をそのまま出力
                out[idx] = input;
            }
        }
    }
}
