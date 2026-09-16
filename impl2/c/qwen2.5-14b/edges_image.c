#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のパディング
    int padded_h = h + 2;
    int padded_w = w + 2;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));

    // 元の画像をパディングされた画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // ガウシアンフィルタのシグマを計算
    double sigma = 0.5 + 2 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)(6 * sigma + 1);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンフィルタのカーネルを計算
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double g = exp(-(i * i + j * j) / (2 * sigma * sigma));
            gaussian_kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = g;
            sum += g;
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        gaussian_kernel[i] /= sum;
    }

    // ガウシアンフィルタを適用
    double* filtered = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(filtered, 0, padded_h * padded_w * sizeof(double));
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    sum += padded_in[(y + ky) * padded_w + (x + kx)] * gaussian_kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                }
            }
            filtered[y * padded_w + x] = sum;
        }
    }

    // 勾配を計算
    double* gradient_magnitude = (double*)malloc(h * w * sizeof(double));
    double* gradient_direction = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = filtered[(y + 1) * padded_w + (x + 2)] - filtered[(y + 1) * padded_w + (x)];
            double dy = filtered[(y + 2) * padded_w + (x + 1)] - filtered[(y) * padded_w + (x + 1)];
            gradient_magnitude[y * w + x] = sqrt(dx * dx + dy * dy);
            gradient_direction[y * w + x] = atan2(dy, dx);
        }
    }

    // 非極大抑制
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double theta = gradient_direction[y * w + x];
            int q = (theta < 0) ? 0 : 1;
            int r = (theta < 0) ? 1 : 0;
            int t = (theta < 0) ? -1 : 1;
            double m = gradient_magnitude[y * w + x];
            double m1 = gradient_magnitude[(y + q) * w + (x + r)];
            double m2 = gradient_magnitude[(y + t) * w + (x - r)];
            if (m >= m1 && m >= m2) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // ヒステリシスしきい値処理
    double low_threshold = 0.1;
    double high_threshold = 0.3;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] == 1.0) {
                if (gradient_magnitude[y * w + x] < low_threshold) {
                    out[y * w + x] = 0.0;
                }
            } else {
                if (gradient_magnitude[y * w + x] > high_threshold) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }

    // メモリ解放
    free(padded_in);
    free(gaussian_kernel);
    free(filtered);
    free(gradient_magnitude);
    free(gradient_direction);
}
