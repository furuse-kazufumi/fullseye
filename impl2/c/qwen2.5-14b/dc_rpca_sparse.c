#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。仕様書に従い無視する。
    // λ の計算。仕様書の説明に従い、λ = (0.5 + 1.5*a) / sqrt(max(h, w)) とする。
    double lambda = (0.5 + 1.5 * a) / sqrt((h > w) ? h : w);

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各画素に対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の画素値を取得
            double input_value = in[y * w + x];

            // スパース項 S の計算。仕様書の説明に従い、S = clip(input_value - 0.5, -lambda, lambda) + 0.5 とする。
            double sparse_value = fmax(fmin(input_value - 0.5, lambda), -lambda) + 0.5;

            // 出力画像に結果を格納
            out[y * w + x] = sparse_value;
        }
    }
}
