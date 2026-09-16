#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b を σ₁, σ₂ に変換
    double sigma1 = 0.5 + a * 2.0; // σ₁ の範囲は 0.5〜2.5
    double sigma2 = 1.0 + b * 4.0; // σ₂ の範囲は 1.0〜5.0

    // ガウシアンカーネルの最大範囲を計算
    int max_range = (int)ceil(3.0 * fmax(sigma1, sigma2));

    // ガウシアンカーネルを生成
    double kernel1[max_range * max_range];
    double kernel2[max_range * max_range];
    double sum1 = 0.0, sum2 = 0.0;
    for (int y = -max_range; y <= max_range; ++y) {
        for (int x = -max_range; x <= max_range; ++x) {
            int idx = (y + max_range) * (max_range * 2 + 1) + (x + max_range);
            double g1 = exp(-(x * x + y * y) / (2.0 * sigma1 * sigma1)) / (2.0 * M_PI * sigma1 * sigma1);
            double g2 = exp(-(x * x + y * y) / (2.0 * sigma2 * sigma2)) / (2.0 * M_PI * sigma2 * sigma2);
            kernel1[idx] = g1;
            kernel2[idx] = g2;
            sum1 += g1;
            sum2 += g2;
        }
    }

    // カーネルを正規化
    for (int i = 0; i < max_range * max_range; ++i) {
        kernel1[i] /= sum1;
        kernel2[i] /= sum2;
    }

    // 出力画像を初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // DoG 操作を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double value1 = 0.0, value2 = 0.0;
            for (int ky = -max_range; ky <= max_range; ++ky) {
                for (int kx = -max_range; kx <= max_range; ++kx) {
                    int idx = (ky + max_range) * (max_range * 2 + 1) + (kx + max_range);
                    int iy = y + ky;
                    int ix = x + kx;
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = 2 * h - iy - 1;
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = 2 * w - ix - 1;
                    value1 += kernel1[idx] * in[iy * w + ix];
                    value2 += kernel2[idx] * in[iy * w + ix];
                }
            }
            out[y * w + x] = value1 - value2;
        }
    }

    // 出力を正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_val) max_val = out[i];
    }
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_val;
    }
}
