#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a に基づいて核サイズを選択 (3, 5, 7, 9 の 4 段階)
    int kernel_size;
    if (a < 0.25) {
        kernel_size = 3;
    } else if (a < 0.5) {
        kernel_size = 5;
    } else if (a < 0.75) {
        kernel_size = 7;
    } else {
        kernel_size = 9;
    }

    // 端の扱い: 端画素を重複させて折り返す (reflect)
    int half_kernel = kernel_size / 2;
    double* temp = (double*)malloc(h * w * sizeof(double));

    // 横方向のフィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int k = -half_kernel; k <= half_kernel; k++) {
                int x_reflect = x + k;
                if (x_reflect < 0) {
                    x_reflect = -x_reflect - 1;
                } else if (x_reflect >= w) {
                    x_reflect = 2 * w - x_reflect - 1;
                }
                double weight = 1.0; // 二項係数はここでは 1 として扱う
                sum += in[y * w + x_reflect] * weight;
                weight_sum += weight;
            }
            temp[y * w + x] = sum / weight_sum;
        }
    }

    // 縦方向のフィルタリング
    for (int x = 0; x < w; x++) {
        for (int y = 0; y < h; y++) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int k = -half_kernel; k <= half_kernel; k++) {
                int y_reflect = y + k;
                if (y_reflect < 0) {
                    y_reflect = -y_reflect - 1;
                } else if (y_reflect >= h) {
                    y_reflect = 2 * h - y_reflect - 1;
                }
                double weight = 1.0; // 二項係数はここでは 1 として扱う
                sum += temp[y_reflect * w + x] * weight;
                weight_sum += weight;
            }
            out[y * w + x] = sum / weight_sum;
        }
    }

    free(temp);
}
