#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は使用しない
    (void)b;

    // σ の計算。a は [0,1] の範囲だが、σ は [0.5, 3.0] の範囲にマッピングする。
    double sigma = 0.5 + a * 2.5;

    // ガウシアンカーネルのサイズを計算。σ の 3 倍のサイズを取る。
    int kernel_size = (int)ceil(3 * sigma);
    // カーネルの中心位置
    int center = kernel_size / 2;

    // ラプラシアンカーネルの計算
    double laplace_kernel[kernel_size * kernel_size];
    for (int y = -center; y <= center; ++y) {
        for (int x = -center; x <= center; ++x) {
            int idx = (y + center) * kernel_size + (x + center);
            laplace_kernel[idx] = (x * x + y * y - 2 * sigma * sigma) * exp(-(x * x + y * y) / (2 * sigma * sigma)) / (2 * M_PI * sigma * sigma * sigma * sigma);
        }
    }

    // 出力画像の最大値を計算するための変数
    double max_out = 0.0;

    // 画像の各ピクセルに対してラプラシアン・オブ・ガウシアンを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -center; ky <= center; ++ky) {
                for (int kx = -center; kx <= center; ++kx) {
                    int in_idx = (y + ky) * w + (x + kx);
                    int kernel_idx = (ky + center) * kernel_size + (kx + center);
                    // 画像の端を処理するための境界条件
                    if (in_idx >= 0 && in_idx < h * w) {
                        sum += in[in_idx] * laplace_kernel[kernel_idx];
                    }
                }
            }
            out[y * w + x] = fabs(sum);
            if (out[y * w + x] > max_out) {
                max_out = out[y * w + x];
            }
        }
    }

    // 出力を最大値で正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
