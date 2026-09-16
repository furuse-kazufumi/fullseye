#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ガウシアンぼかしのシグマを計算
    double sigma = 0.3 + 2.7 * a;

    // 5x5 ガウシアンカーネルの係数を計算
    double kernel[5][5];
    double sum = 0.0;
    for (int ky = -2; ky <= 2; ky++) {
        for (int kx = -2; kx <= 2; kx++) {
            double dx = kx * kx;
            double dy = ky * ky;
            double g = exp(-(dx + dy) / (2 * sigma * sigma));
            kernel[ky + 2][kx + 2] = g;
            sum += g;
        }
    }
    for (int ky = -2; ky <= 2; ky++) {
        for (int kx = -2; kx <= 2; kx++) {
            kernel[ky + 2][kx + 2] /= sum;
        }
    }

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // ガウシアンぼかしを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -2; ky <= 2; ky++) {
                for (int kx = -2; kx <= 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の扱い: BORDER_REFLECT_101
                    if (ny < 0) ny = -ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    sum += in[ny * w + nx] * kernel[ky + 2][kx + 2];
                }
            }
            out[y * w + x] = sum;
        }
    }
}
