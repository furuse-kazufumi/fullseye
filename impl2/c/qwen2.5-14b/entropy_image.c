#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓の半径を計算
    int radius = (int)(a * 3 + 0.5); // a は [0, 1] の範囲で、半径は 1 から 4 まで
    radius = fmax(1, fmin(radius, 4)); // 半径は 1 から 4 の範囲に制限

    // エントロピー計算用の配列
    double histogram[256] = {0};
    double entropy = 0.0;
    double total = 0.0;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各ピクセルに対してエントロピーを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセルをカウント
            memset(histogram, 0, sizeof(histogram));
            total = 0.0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        int value = (int)(in[ny * w + nx] * 255 + 0.5); // 0-1 の範囲を 0-255 に変換
                        histogram[value]++;
                        total++;
                    }
                }
            }

            // エントロピーを計算
            entropy = 0.0;
            for (int i = 0; i < 256; i++) {
                if (histogram[i] > 0) {
                    double p = histogram[i] / total;
                    entropy -= p * log2(p);
                }
            }

            // 正規化されたエントロピーを出力画像に設定
            out[y * w + x] = entropy / (log2(256) * total);
        }
    }
}
