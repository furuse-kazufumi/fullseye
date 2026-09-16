#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // σ = 0.3 + 2.7a でガウシアンフィルタを適用
    double sigma = 0.3 + 2.7 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    // カーネルサイズは奇数でなければならない
    int kernel_size = (int)(sigma * 3) + 1;
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルの計算
    double sum = 0.0;
    double kernel[kernel_size];
    int half_kernel = kernel_size / 2;
    for (int i = -half_kernel; i <= half_kernel; i++) {
        kernel[i + half_kernel] = exp(-(i * i) / (2 * sigma * sigma));
        sum += kernel[i + half_kernel];
    }
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 画像の平滑化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_sum = 0.0;
            int count = 0;
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 画像の境界外を処理するための補間
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        pixel_sum += in[ny * w + nx] * kernel[ky + half_kernel] * kernel[kx + half_kernel];
                        count++;
                    }
                }
            }
            out[y * w + x] = pixel_sum / count;
        }
    }
}
