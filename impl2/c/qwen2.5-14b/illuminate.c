#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺のパディングを無視する。ガウシアンぼかしの半径は 3+12*a で、
    // これは 15 までなので、実際には 15 以下の整数値を想定する。
    int radius = (int)(3 + 12 * a);
    int kernel_size = 2 * radius + 1;

    // ガウシアンカーネルの計算
    double sigma = 3 + 12 * a;
    double sum = 0.0;
    double kernel[kernel_size * kernel_size];
    for (int ky = -radius; ky <= radius; ky++) {
        for (int kx = -radius; kx <= radius; kx++) {
            double g = exp(-(kx * kx + ky * ky) / (2 * sigma * sigma));
            kernel[(ky + radius) * kernel_size + (kx + radius)] = g;
            sum += g;
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // ガウシアンぼかしの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double blurred = 0.0;
            int count = 0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        blurred += in[ny * w + nx] * kernel[(ky + radius) * kernel_size + (kx + radius)];
                        count++;
                    }
                }
            }
            blurred /= count;
            out[y * w + x] = in[y * w + x] + b * (in[y * w + x] - blurred);
        }
    }
}
