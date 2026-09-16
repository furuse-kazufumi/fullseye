#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない。
    (void)a;
    (void)b;

    // 指数関数の定数を計算
    const double exp1 = exp(1.0);
    const double norm_factor = (exp1 - 1.0);

    // 入力画像の各ピクセルに対して指数関数を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = (exp(in[idx]) - 1.0) / norm_factor;
        }
    }
}
