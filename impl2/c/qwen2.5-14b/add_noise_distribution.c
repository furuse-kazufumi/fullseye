#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 乱数シードを a から生成
    unsigned int seed = (unsigned int)(a * 997) + 7;
    srand(seed);

    // ノイズの標準偏差を b から計算
    double std_dev = 0.02 + b * 0.2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            out[idx] = in[idx];
        }
    }

    // 画像の各ピクセルに対してガウス分布に基づくノイズを加える
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double noise = std_dev * (double)rand() / RAND_MAX;
            out[idx] += noise;
            // ピクセル値が [0, 1] の範囲外にならないようにクリッピング
            if (out[idx] < 0.0) {
                out[idx] = 0.0;
            } else if (out[idx] > 1.0) {
                out[idx] = 1.0;
            }
        }
    }
}
