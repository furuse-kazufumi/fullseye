#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は [0,1] の範囲で、σ の比を 1.0 から 4.0 に変化させる。
    // σ の比は 1.0 + 3.0 * a で計算される。
    double sigma_ratio = 1.0 + 3.0 * a;

    // 画像の端をどのように処理するか。ここでは、端のピクセルはそのまま使用し、
    // 必要な周囲のピクセルは端のピクセルを使用する。
    // これはガウシアンフィルタリングのための一般的なアプローチである。

    // ガウシアンフィルタリングのためのカーネルサイズを計算
    int kernel_size = (int)ceil(3 * sigma_ratio);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを計算
    double kernel[kernel_size];
    double sum = 0.0;
    for (int i = 0; i < kernel_size; i++) {
        double x = (i - kernel_size / 2) / sigma_ratio;
        kernel[i] = exp(-x * x / 2) / (sqrt(2 * M_PI) * sigma_ratio);
        sum += kernel[i];
    }
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 2つのガウシアンフィルタリングを適用
    double img1[h * w], img2[h * w];
    for (int i = 0; i < h * w; i++) {
        img1[i] = in[i];
        img2[i] = in[i];
    }

    // img1 に対してガウシアンフィルタリングを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        ny = (ny < 0) ? 0 : h - 1;
                        nx = (nx < 0) ? 0 : w - 1;
                    }
                    sum += kernel[ky + kernel_size / 2] * kernel[kx + kernel_size / 2] * img1[ny * w + nx];
                }
            }
            img1[y * w + x] = sum;
        }
    }

    // img2 に対して σ が大きいガウシアンフィルタリングを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        ny = (ny < 0) ? 0 : h - 1;
                        nx = (nx < 0) ? 0 : w - 1;
                    }
                    sum += kernel[ky + kernel_size / 2] * kernel[kx + kernel_size / 2] * img2[ny * w + nx];
                }
            }
            img2[y * w + x] = sum;
        }
    }

    // 2つの画像の差分を計算
    for (int i = 0; i < h * w; i++) {
        out[i] = fabs(img1[i] - img2[i]);
    }

    // 出力を最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_val;
        }
    }
}
