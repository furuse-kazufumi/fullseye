#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の処理は BORDER_REFLECT_101 モードを模倣
    // これは、画像の端を重複させずに折り返す方法で、
    // OpenCV の BORDER_REFLECT_101 モードに対応しています。

    // σ の計算
    double sigma = 0.3 + 2.7 * a;

    // ガウシアンカーネルのサイズを計算
    int kernel_size = (int)ceil(6 * sigma + 1);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルの初期化
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = 0; i < kernel_size; i++) {
        for (int j = 0; j < kernel_size; j++) {
            int y = i - kernel_size / 2;
            int x = j - kernel_size / 2;
            kernel[i * kernel_size + j] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[i * kernel_size + j];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 画像の平滑化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_sum = 0.0;
            for (int ky = 0; ky < kernel_size; ky++) {
                for (int kx = 0; kx < kernel_size; kx++) {
                    int iy = y + ky - kernel_size / 2;
                    int ix = x + kx - kernel_size / 2;
                    // 端の処理
                    if (iy < 0) iy = -iy - 1;
                    if (iy >= h) iy = 2 * h - iy - 1;
                    if (ix < 0) ix = -ix - 1;
                    if (ix >= w) ix = 2 * w - ix - 1;
                    pixel_sum += in[iy * w + ix] * kernel[ky * kernel_size + kx];
                }
            }
            out[y * w + x] = pixel_sum;
        }
    }

    // メモリの解放
    free(kernel);
}
