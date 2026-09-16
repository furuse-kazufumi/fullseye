#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ガウシアンカーネルのシグマを計算
    double sigma = 1 + 3 * a;

    // ガウシアンカーネルのサイズを計算
    int kernel_size = (int)ceil(6 * sigma + 1);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを計算
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 入力画像のガウシアン平滑化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx] * kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                        count++;
                    }
                }
            }
            double smoothed = sum / count;
            double threshold = (b - 0.5) * 0.3;
            out[y * w + x] = (smoothed > threshold) ? 1.0 : 0.0;
        }
    }

    // メモリを解放
    free(kernel);
}
