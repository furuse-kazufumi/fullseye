#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の扱い: 端画素を重複させて折り返す (reflect)
    int window_size = (int)(a * 16) + 1; // a が [0,1] の範囲なので、window_size は 1 から 17 まで
    double eps = 1e-6; // 小さな値を加えてゼロ除算を防ぐ

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double sum_sq = 0.0;
            int count = 0;

            for (int ky = -window_size / 2; ky <= window_size / 2; ky++) {
                for (int kx = -window_size / 2; kx <= window_size / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 端を折り返す (reflect)
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    double pixel = in[ny * w + nx];
                    sum += pixel;
                    sum_sq += pixel * pixel;
                    count++;
                }
            }

            double mean = sum / count;
            double std = sqrt((sum_sq / count) - mean * mean);

            // b で標準偏差の下限を設定
            std = fmax(std, b);

            // Local contrast normalization
            out[y * w + x] = (in[y * w + x] - mean) / (std + eps) + 0.5;
        }
    }
}
