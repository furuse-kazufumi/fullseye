#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Förstner 演算子の適用には、ガウシアンフィルタリングとコーナー検出が含まれる。
    // ここでは、ガウシアンフィルタリングのシグマをパラメータ a で調整し、
    // デフォルトでは 0.5 から 2.5 の範囲で調整可能とする。
    // パラメータ b は使用されないため、無視する。

    // ガウシアンフィルタリングのシグマを計算
    double sigma = 0.5 + a * 2.0; // a の範囲は [0, 1] で、sigma の範囲は [0.5, 2.5]

    // ガウシアンフィルタリングのカーネルサイズを計算
    int kernel_size = (int)(6 * sigma + 1);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを生成
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // ガウシアンフィルタリングを適用
    double* filtered = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ky_filtered = y + ky;
                    int kx_filtered = x + kx;
                    if (ky_filtered >= 0 && ky_filtered < h && kx_filtered >= 0 && kx_filtered < w) {
                        value += in[ky_filtered * w + kx_filtered] * kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                    }
                }
            }
            filtered[y * w + x] = value;
        }
    }

    // コーナー検出を適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double Ix = (filtered[(y + 1) * w + x] - filtered[(y - 1) * w + x]) / 2.0;
            double Iy = (filtered[y * w + x + 1] - filtered[y * w + x - 1]) / 2.0;
            double Ixx = filtered[(y + 1) * w + x] - 2 * filtered[y * w + x] + filtered[(y - 1) * w + x];
            double Iyy = filtered[y * w + x + 1] - 2 * filtered[y * w + x] + filtered[y * w + x - 1];
            double Ixy = (filtered[(y + 1) * w + x + 1] - filtered[(y + 1) * w + x - 1] - filtered[(y - 1) * w + x + 1] + filtered[(y - 1) * w + x - 1]) / 4.0;
            double w = Ixx * Iyy - Ixy * Ixy;
            double q = (Ixx + Iyy) / (2 * sqrt(w + 1e-6)); // 1e-6 はゼロ除算を防ぐための小さな値
            out[y * w + x] = w * q;
        }
    }

    // 出力を最大値で正規化
    double max_value = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_value;
    }

    // メモリを解放
    free(kernel);
    free(filtered);
}
