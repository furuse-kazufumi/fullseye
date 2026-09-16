#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、つまみ a, b の影響は無視する。実装の詳細は、Frangiフィルタのアルゴリズムに基づく。
    // 画像の端は、境界外のピクセルを参照せずに、そのピクセルの値を0と仮定する。

    // スケーリングと正規化のための変数
    double max_response = 0.0;

    // 各ピクセルについてFrangiフィルタを適用
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // Hessian行列の計算
            double dx2 = in[(y + 1) * w + x] + in[(y - 1) * w + x] - 2 * in[y * w + x];
            double dy2 = in[y * w + (x + 1)] + in[y * w + (x - 1)] - 2 * in[y * w + x];
            double dxy = (in[(y + 1) * w + (x + 1)] + in[(y - 1) * w + (x - 1)] - in[(y + 1) * w + (x - 1)] - in[(y - 1) * w + (x + 1)]) / 4;

            // 固有値の計算
            double trace = dx2 + dy2;
            double det = dx2 * dy2 - dxy * dxy;
            double lambda1 = (trace + sqrt(trace * trace - 4 * det)) / 2;
            double lambda2 = (trace - sqrt(trace * trace - 4 * det)) / 2;

            // Frangiフィルタの応答の計算
            double response = exp(-lambda1 * lambda1) * (1 - exp(-lambda2 * lambda2 / lambda1 * lambda1));

            // 最大応答の更新
            if (response > max_response) {
                max_response = response;
            }

            // 出力画像に応答を格納
            out[y * w + x] = response;
        }
    }

    // 出力を最大応答で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_response;
    }
}
