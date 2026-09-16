#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。DoG (Difference of Gaussians) を計算する。
    // 画像の端をガウシアンフィルタリングの際は、境界外のピクセルは端のピクセルを使用する。

    // ガウシアンフィルタリングのパラメータ
    double sigma1 = 1.0;
    double sigma2 = 1.6; // 一般的な DoG の σ の選択

    // ガウシアンフィルタリングのためのカーネルサイズ
    int kernel_size = 5;
    int half_kernel = kernel_size / 2;

    // ガウシアンカーネルの計算
    double kernel[kernel_size * kernel_size];
    double sum = 0.0;
    for (int i = -half_kernel; i <= half_kernel; i++) {
        for (int j = -half_kernel; j <= half_kernel; j++) {
            double x = i, y = j;
            double g = exp(-(x * x + y * y) / (2 * sigma1 * sigma1)) / (2 * M_PI * sigma1 * sigma1);
            kernel[(i + half_kernel) * kernel_size + (j + half_kernel)] = g;
            sum += g;
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // ガウシアンフィルタリングの実行
    double gaussian1[h * w];
    double gaussian2[h * w];
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum1 = 0.0, sum2 = 0.0;
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky, nx = x + kx;
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;
                    sum1 += in[ny * w + nx] * kernel[(ky + half_kernel) * kernel_size + (kx + half_kernel)];
                    sum2 += in[ny * w + nx] * kernel[(ky + half_kernel) * kernel_size + (kx + half_kernel)];
                }
            }
            gaussian1[y * w + x] = sum1;
            gaussian2[y * w + x] = sum2;
        }
    }

    // DoG の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dog = gaussian1[y * w + x] - gaussian2[y * w + x];
            out[y * w + x] = fabs(dog);
        }
    }

    // 最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) max_val = out[i];
    }
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_val;
    }
}
