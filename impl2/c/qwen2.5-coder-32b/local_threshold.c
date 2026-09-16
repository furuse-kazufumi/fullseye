#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ガウスカーネルのサイズとシグマの計算
    int kernel_size = 1 + 3 * a;
    if (kernel_size % 2 == 0) kernel_size++; // 奇数にする
    double sigma = a;
    double offset = (b - 0.5) * 0.3;

    // ガウスカーネルの作成
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    int half_kernel = kernel_size / 2;
    for (int ky = -half_kernel; ky <= half_kernel; ky++) {
        for (int kx = -half_kernel; kx <= half_kernel; kx++) {
            double r = sqrt(kx * kx + ky * ky);
            kernel[(ky + half_kernel) * kernel_size + (kx + half_kernel)] = exp(-(r * r) / (2 * sigma * sigma));
            sum += kernel[(ky + half_kernel) * kernel_size + (kx + half_kernel)];
        }
    }
    // ガウスカーネルの正規化
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 出力画像の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double local_mean = 0.0;
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 境界外のピクセルはゼロパディング
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        local_mean += 0.0;
                    } else {
                        local_mean += in[ny * w + nx] * kernel[(ky + half_kernel) * kernel_size + (kx + half_kernel)];
                    }
                }
            }
            double threshold = local_mean + offset;
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // ガウスカーネルの解放
    free(kernel);
}
