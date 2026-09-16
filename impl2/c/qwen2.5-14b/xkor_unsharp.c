#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a は未使用。つまみ b はシグマを調整する。
    // シグマの範囲は 0.5 から 2.5 まで。b は [0, 1] の範囲で与えられる。
    double sigma = 0.5 + 2.0 * b;

    // 5x5 ガウシアンカーネルの作成
    double kernel[5][5];
    double sum = 0.0;
    for (int y = -2; y <= 2; ++y) {
        for (int x = -2; x <= 2; ++x) {
            double d = sqrt(x * x + y * y);
            kernel[y + 2][x + 2] = exp(-(d * d) / (2 * sigma * sigma));
            sum += kernel[y + 2][x + 2];
        }
    }
    for (int y = 0; y < 5; ++y) {
        for (int x = 0; x < 5; ++x) {
            kernel[y][x] /= sum;
        }
    }

    // 画像の端の処理は反射境界を使用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double blurred = 0.0;
            for (int ky = -2; ky <= 2; ++ky) {
                for (int kx = -2; kx <= 2; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    blurred += in[ny * w + nx] * kernel[ky + 2][kx + 2];
                }
            }
            out[y * w + x] = in[y * w + x] + (in[y * w + x] - blurred);
        }
    }
}
