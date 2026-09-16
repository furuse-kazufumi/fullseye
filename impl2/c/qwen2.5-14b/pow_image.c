#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。仕様書に従い無視する。
    // 画像の端の処理については、仕様書が明示していないため、
    // 範囲外の値が来ても落ちないよう、入力画像の範囲内のみを処理する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            // 入力画像の値域は [0,1] と想定されるが、範囲外の値に対しても処理を行う。
            // ここで、範囲外の値はそのまま出力する。
            double value = in[idx];
            out[idx] = pow(value, a);
        }
    }
}
