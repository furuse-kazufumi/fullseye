#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double sigma = 0.5 + 2.5 * a;  // ガウシアンの標準偏差
    const double pi = 3.14159265358979323846;
    const double inv_pi = 1.0 / pi;

    // ガウシアンラプラシアンフィルタの適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -3; ky <= 3; ++ky) {
                for (int kx = -3; kx <= 3; ++kx) {
                    double dx = (double)kx;
                    double dy = (double)ky;
                    double r2 = dx * dx + dy * dy;
                    double g = exp(-r2 / (2.0 * sigma * sigma)) / (2.0 * pi * sigma * sigma * sigma);
                    double laplacian = (r2 - 2.0 * sigma * sigma) * g;
                    int src_x = x + kx;
                    int src_y = y + ky;
                    if (src_x >= 0 && src_x < w && src_y >= 0 && src_y < h) {
                        sum += laplacian * in[src_y * w + src_x];
                    }
                }
            }
            // 出力を符号付き01に正規化
            out[y * w + x] = (sum >= 0) ? (sum + 1.0) / 2.0 : (1.0 - sum) / 2.0;
        }
    }
}
