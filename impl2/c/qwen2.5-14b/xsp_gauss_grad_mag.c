#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ガウシアンフィルタのシグマを計算
    double sigma = 0.5 + 2.5 * a;

    // ガウシアンフィルタのカーネルサイズを計算
    int kernel_size = (int)ceil(3 * sigma);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンフィルタのカーネルを計算
    double* gaussian_kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            gaussian_kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += gaussian_kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        gaussian_kernel[i] /= sum;
    }

    // ガウシアンフィルタを適用
    double* blurred = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = 2 * h - iy - 1;
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = 2 * w - ix - 1;
                    value += in[iy * w + ix] * gaussian_kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                }
            }
            blurred[y * w + x] = value;
        }
    }

    // 勾配を計算
    double* dx = (double*)malloc(h * w * sizeof(double));
    double* dy = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = 2 * h - iy - 1;
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = 2 * w - ix - 1;
                    value += blurred[iy * w + ix] * (kx == 0 ? 0 : (kx == -1 ? -1 : 1));
                }
            }
            dx[y * w + x] = value;
        }
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky;
                    int ix = x + kx;
                    if (iy < 0) iy = -iy;
                    if (iy >= h) iy = 2 * h - iy - 1;
                    if (ix < 0) ix = -ix;
                    if (ix >= w) ix = 2 * w - ix - 1;
                    value += blurred[iy * w + ix] * (ky == 0 ? 0 : (ky == -1 ? -1 : 1));
                }
            }
            dy[y * w + x] = value;
        }
    }

    // 勾配の大きさを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = sqrt(dx[y * w + x] * dx[y * w + x] + dy[y * w + x] * dy[y * w + x]);
        }
    }

    // 最大値で正規化
    double max_value = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (out[y * w + x] > max_value) {
                max_value = out[y * w + x];
            }
        }
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] /= max_value;
        }
    }

    // メモリを解放
    free(gaussian_kernel);
    free(blurred);
    free(dx);
    free(dy);
}
