#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int d = 5; // カーネル直径
    double sigmaSpace = 1.0 + 3.0 * a; // 空間方向の広がり
    double sigmaColor = 0.05 + 0.4 * b; // 輝度方向の許容差
    double sigmaSpace2 = 2.0 * sigmaSpace * sigmaSpace;
    double sigmaColor2 = 2.0 * sigmaColor * sigmaColor;

    // カーネルの範囲を計算
    int radius = d / 2;

    // 各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weightSum = 0.0;

            // カーネル範囲内のピクセルに対して重みを計算
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界外のピクセルは無視 (ゼロパディング)
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double spatialWeight = exp(-(ky * ky + kx * kx) / sigmaSpace2);
                        double colorWeight = exp(-(in[ny * w + nx] - in[y * w + x]) * (in[ny * w + nx] - in[y * w + x]) / sigmaColor2);
                        double weight = spatialWeight * colorWeight;

                        sum += in[ny * w + nx] * weight;
                        weightSum += weight;
                    }
                }
            }

            // 重み付き平均を計算
            out[y * w + x] = weightSum > 0.0 ? sum / weightSum : in[y * w + x];
        }
    }
}
