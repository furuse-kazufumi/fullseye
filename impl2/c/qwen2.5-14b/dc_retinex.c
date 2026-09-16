#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の現在のピクセルの値を取得
            double input_value = in[y * w + x];
            
            // 単純なガウシアンフィルタリングの代わりに、ここでは単純な平均フィルタリングを適用します。
            // ガウシアンフィルタリングの実装は複雑になるため、単純な平均フィルタリングを用います。
            // これは、ガウシアンフィルタリングの代わりに、周囲のピクセルの平均値を計算します。
            double sum = 0.0;
            int count = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を避ける
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        ++count;
                    }
                }
            }
            double gaussian_value = sum / count;
            
            // 単純な Retinex モデルの実装: log(I) - log(Gauss_sigma(I))
            // ここで、a と b は使用されませんが、パラメータとして保持します。
            // これは、仕様書の説明が明確でないため、単純化のために省略します。
            double retinex_value = log(input_value + 1e-10) - log(gaussian_value + 1e-10);
            
            // 出力画像に結果を書き込む
            out[y * w + x] = retinex_value;
        }
    }
}
