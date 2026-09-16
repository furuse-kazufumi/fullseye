#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // フィルタ強度 h の計算
    double h_value = 3 + 20 * a;

    // パッチサイズと探索窓サイズ
    int templateWindowSize = 7;
    int searchWindowSize = 21;

    // 画像の端をどのように処理するか: ここでは、画像の端は境界値を保持するように処理する。
    // つまり、端のピクセルはその値を出力にそのままコピーする。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 非局所平均法の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weightSum = 0.0;

            // パッチの中心ピクセル
            double centerPixel = in[y * w + x];

            // 探索窓内の各ピクセルに対して
            for (int dy = -searchWindowSize / 2; dy <= searchWindowSize / 2; dy++) {
                for (int dx = -searchWindowSize / 2; dx <= searchWindowSize / 2; dx++) {
                    int py = y + dy;
                    int px = x + dx;

                    // 画像の境界外を避ける
                    if (py < 0 || py >= h || px < 0 || px >= w) continue;

                    // パッチの中心からの距離
                    double distance = sqrt(dy * dy + dx * dx);

                    // パッチの類似度の計算
                    double similarity = exp(-distance * distance / (2 * h_value * h_value));

                    // 重み付き平均の計算
                    sum += in[py * w + px] * similarity;
                    weightSum += similarity;
                }
            }

            // 重み付き平均を出力画像に書き込む
            if (weightSum > 0) {
                out[y * w + x] = sum / weightSum;
            }
        }
    }
}
