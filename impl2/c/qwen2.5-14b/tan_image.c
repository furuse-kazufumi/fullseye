#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。
    // 画像の各画素に対して正接関数を適用する。
    // 入力画像の画素値は [0, 1] の範囲であると想定するが、範囲外の値が来ても処理を続行する。
    // 出力画像の画素値は符号付き値を [0, 1] に写す (signed01) ことで表現する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            // 画素値を [-0.45π, 0.45π] の範囲にマッピング
            double angle = (pixel - 0.5) * M_PI * 0.9;
            // 正接関数を適用
            double tan_value = tan(angle);
            // 結果を [0, 1] の範囲にマッピング
            out[y * w + x] = (tan_value + 1.0) / 2.0;
        }
    }
}
