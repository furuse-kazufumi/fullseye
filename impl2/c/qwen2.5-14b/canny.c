#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ガウシアンフィルタのσを計算
    double sigma = 0.5 + a * 1.5; // a は [0,1] の範囲で、σは [0.5, 2.0] の範囲にマッピング
    double sigma2 = sigma * sigma;
    double pi = 3.14159265358979323846;
    
    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)(6 * sigma + 1);
    if (kernel_size % 2 == 0) kernel_size++; // カーネルサイズは奇数でなければならない
    
    // ガウシアンフィルタのカーネルを生成
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = 0; i < kernel_size; i++) {
        for (int j = 0; j < kernel_size; j++) {
            int x = i - kernel_size / 2;
            int y = j - kernel_size / 2;
            gaussian_kernel[i * kernel_size + j] = exp(-(x * x + y * y) / (2 * sigma2)) / (2 * pi * sigma2);
            sum += gaussian_kernel[i * kernel_size + j];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        gaussian_kernel[i] /= sum; // カーネルを正規化
    }
    
    // 入力画像をガウシアンフィルタで平滑化
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int sy = y + ky;
                    int sx = x + kx;
                    if (sy >= 0 && sy < h && sx >= 0 && sx < w) {
                        sum += in[sy * w + sx] * gaussian_kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                    }
                }
            }
            smoothed[y * w + x] = sum;
        }
    }
    free(gaussian_kernel);
    
    // ソベルフィルタを適用
    double* sobel_x = (double*)malloc(h * w * sizeof(double));
    double* sobel_y = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double gx = 0.0, gy = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int sy = y + ky;
                    int sx = x + kx;
                    if (sy >= 0 && sy < h && sx >= 0 && sx < w) {
                        double dx = -1 * kx, dy = -1 * ky;
                        gx += smoothed[sy * w + sx] * (dx * dx + dy * dy);
                        gy += smoothed[sy * w + sx] * (dx * dx + dy * dy);
                    }
                }
            }
            sobel_x[y * w + x] = gx;
            sobel_y[y * w + x] = gy;
        }
    }
    free(smoothed);
    
    // ソベル勾配強度を計算
    double* gradient_magnitude = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            gradient_magnitude[y * w + x] = sqrt(sobel_x[y * w + x] * sobel_x[y * w + x] + sobel_y[y * w + x] * sobel_y[y * w + x]);
        }
    }
    free(sobel_x);
    free(sobel_y);
    
    // しきい値処理
    double threshold = b * 0.5; // b は [0,1] の範囲で、しきい値は [0.1, 0.6] の範囲にマッピング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (gradient_magnitude[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }
    free(gradient_magnitude);
}
