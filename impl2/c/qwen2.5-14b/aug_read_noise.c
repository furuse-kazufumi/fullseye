#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ノイズの標準偏差を計算
    double sigma = 0.005 + 0.15 * a;
    double row_bias_std = 0.5 * b * sigma;

    // 乱数シードを設定
    unsigned int seed = (unsigned int)(a * 1000 + b * 1000);
    srand(seed);

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 行ごとに処理
    for (int y = 0; y < h; y++) {
        // 行ごとのバイアスを生成
        double row_bias = (double)rand() / RAND_MAX * 2.0 * row_bias_std - row_bias_std;

        // 行内の各ピクセルに対してノイズを追加
        for (int x = 0; x < w; x++) {
            double pixel = in[y * w + x];
            double noise = (double)rand() / RAND_MAX * 2.0 * sigma - sigma;
            out[y * w + x] = pixel + noise + row_bias;

            // 出力の範囲を [0, 1] にクリップ
            if (out[y * w + x] < 0.0) {
                out[y * w + x] = 0.0;
            } else if (out[y * w + x] > 1.0) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
