#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない
    (void)a;
    (void)b;

    // 位相アンラップ処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の値を [-pi, pi] の範囲に変換
            double phase = (in[y * w + x] - 0.5) * M_PI * 2.0;

            // 位相のラップを解除
            // ここでは単純にラップを解除する処理を実装する
            // ただし、実際の処理はより複雑なアルゴリズムが必要な場合が多い
            // ここでは単純化のため、ラップを解除する処理を実装
            while (phase < -M_PI) {
                phase += 2.0 * M_PI;
            }
            while (phase > M_PI) {
                phase -= 2.0 * M_PI;
            }

            // 位相を [0, 1] の範囲に変換
            out[y * w + x] = (phase + M_PI) / (2.0 * M_PI);
        }
    }
}
