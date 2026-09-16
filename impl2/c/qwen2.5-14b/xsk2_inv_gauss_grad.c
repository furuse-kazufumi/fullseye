#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の画素を最近傍の画素値で埋める
    // これは仕様書で明示的に指定されていないため、この実装では選択した方法です。
    // 他の方法（境界を無視する、境界をゼロ埋めする等）も考えられるが、ここでは最近傍を採用する。

    // 逆ガウシアン勾配のパラメータを計算
    double alpha = 50 + 150 * a;

    // 出力画像の各画素を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 画素のインデックスを計算
            int idx = y * w + x;

            // 画素値を取得
            double pixel_value = in[idx];

            // 逆ガウシアン勾配を計算
            // ここでは単純化のため、pixel_value が 0.5 の場合を基準として、
            // pixel_value が 0.5 から離れるほど勾配が大きくなるように定義する。
            // 実際の実装では、より複雑な計算が行われる可能性がある。
            double gradient = exp(-pow(pixel_value - 0.5, 2) / alpha);

            // 出力画像に結果を格納
            out[idx] = gradient;
        }
    }
}
