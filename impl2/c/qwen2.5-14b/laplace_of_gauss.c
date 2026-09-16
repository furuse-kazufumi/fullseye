#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理するためのパディング
    // ここでは、画像の端をゼロパディングする。
    // これは、ガウスフィルタリングとラプラシアンフィルタリングの両方で一般的な手法です。
    // 画像の端の値は、パディングされた領域で計算されます。

    // ガウスフィルタのシグマを計算
    double sigma = 0.5 + 2.5 * a; // a は [0, 1] の範囲で、sigma は [0.5, 3.0] の範囲にマッピングされる

    // ガウスフィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(6 * sigma);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウスフィルタのカーネルを計算
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i;
            double y = j;
            double g = exp(-(x * x + y * y) / (2 * sigma * sigma)) / (2 * M_PI * sigma * sigma);
            gaussian_kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = g;
            sum += g;
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        gaussian_kernel[i] /= sum;
    }

    // 入力画像に対してガウスフィルタを適用
    double* blurred = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int py = y + ky;
                    int px = x + kx;
                    if (py >= 0 && py < h && px >= 0 && px < w) {
                        value += in[py * w + px] * gaussian_kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                    }
                }
            }
            blurred[y * w + x] = value;
        }
    }

    // ラプラシアンフィルタを適用
    double* laplacian_kernel = (double*)malloc(3 * 3 * sizeof(double));
    laplacian_kernel[0] = 1.0;
    laplacian_kernel[1] = 1.0;
    laplacian_kernel[2] = 1.0;
    laplacian_kernel[3] = 1.0;
    laplacian_kernel[4] = -8.0;
    laplacian_kernel[5] = 1.0;
    laplacian_kernel[6] = 1.0;
    laplacian_kernel[7] = 1.0;
    laplacian_kernel[8] = 1.0;

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int py = y + ky;
                    int px = x + kx;
                    if (py >= 0 && py < h && px >= 0 && px < w) {
                        value += blurred[py * w + px] * laplacian_kernel[(ky + 1) * 3 + (kx + 1)];
                    }
                }
            }
            out[y * w + x] = value;
        }
    }

    // メモリを解放
    free(gaussian_kernel);
    free(blurred);
    free(laplacian_kernel);
}
