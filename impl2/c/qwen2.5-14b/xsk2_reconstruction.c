#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は無視する
    (void)b;

    // シード画像の生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double seed_value = in[idx] - (0.05 + 0.25 * a);
            out[idx] = seed_value < 0 ? 0 : seed_value; // シード画像の値は 0 以上
        }
    }

    // マスク画像は入力画像そのもの
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = fmax(out[idx], in[idx]); // シード画像とマスク画像の最大値を出力
        }
    }
}
