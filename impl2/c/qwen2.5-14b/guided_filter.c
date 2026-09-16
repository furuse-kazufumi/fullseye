#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺のパディングは、境界のピクセルをそのままコピーする。
    // これは、入力画像の端を平滑化する際の一般的な手法であり、
    // 辺の情報が失われることを防ぐ。

    // 辺のパディング処理
    for (int y = 0; y < h; ++y) {
        out[y * w] = in[y * w]; // 左端
        out[y * w + w - 1] = in[y * w + w - 1]; // 右端
    }
    for (int x = 0; x < w; ++x) {
        out[x] = in[x]; // 上端
        out[(h - 1) * w + x] = in[(h - 1) * w + x]; // 下端
    }

    // バイラテラルフィルタの適用
    double sigma_s = a * 10; // 空間シグマ
    double sigma_r = b * 0.2; // 輝度シグマ
    int radius = (int)(sigma_s * 3); // フィルタの半径

    // フィルタリング
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double sum_w = 0.0;
            double sum_iw = 0.0;
            for (int ky = -radius; ky <= radius; ++ky) {
                for (int kx = -radius; kx <= radius; ++kx) {
                    int i = y + ky;
                    int j = x + kx;
                    if (i < 0 || i >= h || j < 0 || j >= w) continue;
                    double g = exp(-((ky * ky + kx * kx) / (2 * sigma_s * sigma_s) + (in[i * w + j] - in[y * w + x]) * (in[i * w + j] - in[y * w + x]) / (2 * sigma_r * sigma_r)));
                    sum_w += g;
                    sum_iw += in[i * w + j] * g;
                }
            }
            out[y * w + x] = sum_iw / sum_w;
        }
    }
}
