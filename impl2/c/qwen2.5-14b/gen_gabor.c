#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書では端の扱いが明示的に定義されていないため、端の画素を重複させて折り返す方法を採用する。
    // これは scipy の既定の border_mode "reflect" に準拠する。

    // Gabor カーネルのパラメータ設定
    double theta = M_PI * a;  // 方向 θ
    double nu = 0.1 + 0.3 * b;  // 周波数 ν

    // Gabor カーネルの生成
    int kernel_size = 3;  // カーネルのサイズ (3x3)
    double kernel[kernel_size * kernel_size];
    for (int ky = -1; ky <= 1; ky++) {
        for (int kx = -1; kx <= 1; kx++) {
            double x = kx * cos(theta) + ky * sin(theta);
            double y = -kx * sin(theta) + ky * cos(theta);
            kernel[(ky + 1) * kernel_size + (kx + 1)] = exp(-M_PI * (x * x + y * y) / (nu * nu)) * cos(2 * M_PI * nu * x);
        }
    }

    // L1 ノルムの計算
    double l1_norm = 0.0;
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        l1_norm += fabs(kernel[i]);
    }

    // 畳み込みの実行
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double conv_result = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int py = y + ky;
                    int px = x + kx;
                    // 端の画素を重複させて折り返す
                    if (py < 0) py = -py - 1;
                    if (py >= h) py = 2 * h - py - 1;
                    if (px < 0) px = -px - 1;
                    if (px >= w) px = 2 * w - px - 1;
                    conv_result += in[py * w + px] * kernel[(ky + 1) * kernel_size + (kx + 1)];
                }
            }
            out[y * w + x] = fabs(conv_result) / l1_norm;
        }
    }
}
