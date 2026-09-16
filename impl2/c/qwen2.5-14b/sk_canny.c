#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double sigma_min = 0.5;
    const double sigma_max = 2.5;
    const double sigma = sigma_min + (sigma_max - sigma_min) * a;
    const double gaussian_kernel_size = 3.0 * sigma;
    const int kernel_radius = (int)gaussian_kernel_size;
    const int kernel_size = 2 * kernel_radius + 1;
    const double pi = 3.14159265358979323846;

    // ガウシアンカーネルの計算
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    for (int i = -kernel_radius; i <= kernel_radius; i++) {
        for (int j = -kernel_radius; j <= kernel_radius; j++) {
            int index = (i + kernel_radius) * kernel_size + (j + kernel_radius);
            gaussian_kernel[index] = exp(-(i * i + j * j) / (2 * sigma * sigma)) / (2 * pi * sigma * sigma);
        }
    }

    // 入力画像のガウシアン平滑化
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_radius; ky <= kernel_radius; ky++) {
                for (int kx = -kernel_radius; kx <= kernel_radius; kx++) {
                    int sy = y + ky;
                    int sx = x + kx;
                    if (sy >= 0 && sy < h && sx >= 0 && sx < w) {
                        sum += in[sy * w + sx] * gaussian_kernel[(ky + kernel_radius) * kernel_size + (kx + kernel_radius)];
                    }
                }
            }
            smoothed[y * w + x] = sum;
        }
    }

    // 勾配の計算
    double* gradient_magnitude = (double*)malloc(h * w * sizeof(double));
    double* gradient_direction = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = 0.5 * (smoothed[(y + 1) * w + x] - smoothed[(y - 1) * w + x]);
            double dy = 0.5 * (smoothed[y * w + x + 1] - smoothed[y * w + x - 1]);
            gradient_magnitude[y * w + x] = sqrt(dx * dx + dy * dy);
            gradient_direction[y * w + x] = atan2(dy, dx);
        }
    }

    // 非極大抑制
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double direction = gradient_direction[y * w + x];
            int angle = direction * 180 / pi;
            if (angle < 0) angle += 360;
            if (angle >= 0 && angle < 22.5 || angle >= 157.5 && angle < 202.5 || angle >= 337.5 && angle < 360) {
                if (gradient_magnitude[y * w + x] > gradient_magnitude[(y - 1) * w + x] && gradient_magnitude[y * w + x] > gradient_magnitude[(y + 1) * w + x]) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            } else if (angle >= 22.5 && angle < 67.5 || angle >= 202.5 && angle < 247.5) {
                if (gradient_magnitude[y * w + x] > gradient_magnitude[y * w + x - 1] && gradient_magnitude[y * w + x] > gradient_magnitude[y * w + x + 1]) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            } else if (angle >= 67.5 && angle < 112.5 || angle >= 247.5 && angle < 292.5) {
                if (gradient_magnitude[y * w + x] > gradient_magnitude[(y - 1) * w + x - 1] && gradient_magnitude[y * w + x] > gradient_magnitude[(y + 1) * w + x + 1]) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            } else if (angle >= 112.5 && angle < 157.5 || angle >= 292.5 && angle < 337.5) {
                if (gradient_magnitude[y * w + x] > gradient_magnitude[(y - 1) * w + x + 1] && gradient_magnitude[y * w + x] > gradient_magnitude[(y + 1) * w + x - 1]) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            }
        }
    }

    // ヒステリシスしきい値処理
    double low_threshold = 0.1; // 仮の低しきい値
    double high_threshold = 0.3; // 仮の高しきい値
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            if (gradient_magnitude[y * w + x] > high_threshold) {
                out[y * w + x] = 1.0;
            } else if (gradient_magnitude[y * w + x] > low_threshold) {
                out[y * w + x] = 0.5; // 仮の値
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // メモリ解放
    free(gaussian_kernel);
    free(smoothed);
    free(gradient_magnitude);
    free(gradient_direction);
}
