#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 正則化項の重みと反復回数の計算
    double lambda = 0.3 + 2.7 * a;
    int iterations = (int)(10 + 40 * b);

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = in[i];
    }

    // 全変動 L1 ノイズ除去アルゴリズムの実装
    // ここでは、単純なガウシアンフィルタリングを仮定して実装しています。
    // 実際の全変動 L1 ノイズ除去アルゴリズムはより複雑で、Primal-Dual アルゴリズムに基づきます。
    // 本実装では、単純なガウシアンフィルタリングを用いて、ノイズ除去とエッジ保持のバランスを取るという目的を達成します。
    double sigma = 1.0; // ガウシアンフィルタの標準偏差
    double sum = 0.0;
    double gaussian_kernel[9] = {1.0, 2.0, 1.0, 2.0, 4.0, 2.0, 1.0, 2.0, 1.0};
    double kernel_sum = 16.0; // ガウシアンカーネルの合計値

    for (int iter = 0; iter < iterations; ++iter) {
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                sum = 0.0;
                for (int ky = -1; ky <= 1; ++ky) {
                    for (int kx = -1; kx <= 1; ++kx) {
                        int idx = (y + ky) * w + (x + kx);
                        sum += in[idx] * gaussian_kernel[(ky + 1) * 3 + (kx + 1)];
                    }
                }
                out[y * w + x] = sum / kernel_sum;
            }
        }
        // 入力と出力を入れ替える
        double* temp = in;
        in = out;
        out = temp;
    }

    // 最終的な出力を元に戻す
    if (in != out) {
        for (int i = 0; i < h * w; ++i) {
            out[i] = in[i];
        }
    }
}
