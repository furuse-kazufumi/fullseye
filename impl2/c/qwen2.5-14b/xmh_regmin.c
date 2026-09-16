#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 平滑化の強さを調整
    double sigma = a * 2.0 + 0.15; // 0.15 から 3.15 の範囲に調整

    // ガウシアンカーネルのサイズを決定
    int kernel_size = (int)(sigma * 3.0 + 0.5);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを生成
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2.0 * sigma * sigma));
            sum += kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // 平滑化処理
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int ny = y + ky, nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx] * kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)];
                        count++;
                    }
                }
            }
            smoothed[y * w + x] = sum / count;
        }
    }

    // 局所的な極小点を抽出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = smoothed[y * w + x];
            int min_count = 1;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky, nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (smoothed[ny * w + nx] < min_val) {
                            min_val = smoothed[ny * w + nx];
                            min_count = 1;
                        } else if (smoothed[ny * w + nx] == min_val) {
                            min_count++;
                        }
                    }
                }
            }
            out[y * w + x] = (min_count == 1 && min_val == smoothed[y * w + x]) ? 1.0 : 0.0;
        }
    }

    // メモリを解放
    free(kernel);
    free(smoothed);
}
