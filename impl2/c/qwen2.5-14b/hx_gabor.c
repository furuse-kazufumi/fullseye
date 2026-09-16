#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Gabor フィルタのパラメータ設定
    double theta = a * M_PI;  // 方位
    double freq = 0.08 + 0.35 * b;  // 周波数

    // Gabor フィルタのカーネルサイズを決定
    int kernel_size = 3;  // 3x3 カーネルを使用
    double kernel[kernel_size * kernel_size];
    double sum_kernel = 0.0;

    // Gabor フィルタのカーネルを計算
    for (int ky = -1; ky <= 1; ky++) {
        for (int kx = -1; kx <= 1; kx++) {
            double x = kx * cos(theta) + ky * sin(theta);
            double y = -kx * sin(theta) + ky * cos(theta);
            double g = exp(-M_PI * (x * x + (freq * y) * (freq * y)));
            double f = cos(2 * M_PI * freq * x);
            kernel[(ky + 1) * kernel_size + (kx + 1)] = g * f;
            sum_kernel += fabs(kernel[(ky + 1) * kernel_size + (kx + 1)]);
        }
    }

    // 出力画像の各ピクセルに対して Gabor フィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double conv_sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ky_wrap = (y + ky + h) % h;
                    int kx_wrap = (x + kx + w) % w;
                    conv_sum += in[ky_wrap * w + kx_wrap] * kernel[(ky + 1) * kernel_size + (kx + 1)];
                }
            }
            out[y * w + x] = conv_sum / sum_kernel;
        }
    }
}
