#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が窓の一辺を 3, 5, 7, 9 の4段階に切り替える
    int kernel_size = (int)(a * 4.0);
    if (kernel_size == 0) kernel_size = 3;
    else if (kernel_size == 1) kernel_size = 5;
    else if (kernel_size == 2) kernel_size = 7;
    else kernel_size = 9;

    int half_kernel = kernel_size / 2;

    // 画像の端をどう埋めるか: 境界外のピクセルには 0 を使用する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            out[y * w + x] = sum / count;
        }
    }
}
