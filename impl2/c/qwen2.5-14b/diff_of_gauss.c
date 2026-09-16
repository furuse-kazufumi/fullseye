#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の扱い: 入力画像の端を重複させて折り返す
    // これは、入力画像の境界画素を周囲の画素で埋める方法です。
    // これは仕様書で明示的に指定されていないため、この方法を選択しました。

    // シグマの計算
    double sigma1 = a * 1.5 + 0.5; // 0.5 から 2.5 の範囲
    double sigma2 = b * 4.0 + 1.0; // 1.0 から 5.0 の範囲

    // ガウシアンカーネルのサイズと重みの計算
    int kernel_size = (int)(3.0 * sigma2 + 0.5) + 1; // カーネルサイズは奇数
    double kernel[kernel_size * kernel_size];
    double sum1 = 0.0, sum2 = 0.0;

    for (int y = 0; y < kernel_size; y++) {
        for (int x = 0; x < kernel_size; x++) {
            int ky = y - kernel_size / 2;
            int kx = x - kernel_size / 2;
            double d = sqrt(ky * ky + kx * kx);
            kernel[y * kernel_size + x] = exp(-0.5 * (d * d / (sigma1 * sigma1)));
            sum1 += kernel[y * kernel_size + x];
            kernel[y * kernel_size + x] = exp(-0.5 * (d * d / (sigma2 * sigma2)));
            sum2 += kernel[y * kernel_size + x];
        }
    }

    // カーネルの正規化
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum1;
        kernel[i + kernel_size * kernel_size] /= sum2;
    }

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double conv1 = 0.0, conv2 = 0.0;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int iy = y + ky - kernel_size / 2;
                    int ix = x + kx - kernel_size / 2;
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = h - (iy - h);
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = w - (ix - w);
                    conv1 += in[iy * w + ix] * kernel[ky * kernel_size + kx];
                    conv2 += in[iy * w + ix] * kernel[ky * kernel_size + kx + kernel_size * kernel_size];
                }
            }
            out[y * w + x] = fabs(conv1 - conv2);
        }
    }

    // 出力画像の正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) max_val = out[i];
    }
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_val;
    }
}
