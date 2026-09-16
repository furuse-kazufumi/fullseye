#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは端のピクセルを使用する。
    // これは、画像の端を平滑化する際の一般的な手法であり、境界外のピクセルが存在しない場合の対処法である。

    double sigmaColor = 0.05 + 0.4 * b;
    double sigmaSpace = 1.0 + 3.0 * a;
    int d = 5; // カーネルの直径は固定値5とする

    // バイラテラルフィルタリングの適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            double weightSum = 0.0;

            for (int ky = -d / 2; ky <= d / 2; ++ky) {
                for (int kx = -d / 2; kx <= d / 2; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 端の処理
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;

                    double spatialWeight = exp(-(kx * kx + ky * ky) / (2 * sigmaSpace * sigmaSpace));
                    double colorWeight = exp(-fabs(in[y * w + x] - in[ny * w + nx]) / (2 * sigmaColor * sigmaColor));
                    double weight = spatialWeight * colorWeight;

                    sum += in[ny * w + nx] * weight;
                    weightSum += weight;
                }
            }

            out[y * w + x] = sum / weightSum;
        }
    }
}
