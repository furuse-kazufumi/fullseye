#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 線形ぼかしの方向と長さを計算
    double angle = M_PI * a;  // 方向角 (0 から π)
    double length = 5 + 10 * b;  // ぼかしの長さ (5 から 15)

    // カーネルの長さを計算
    int kernel_length = (int)length;
    if (kernel_length % 2 == 0) {
        kernel_length++;  // カーネルの長さは奇数でなければならない
    }

    // カーネルの中心位置
    int kernel_center = kernel_length / 2;

    // カーネルの各要素を計算
    double kernel[kernel_length];
    for (int i = 0; i < kernel_length; i++) {
        double dx = (i - kernel_center) * cos(angle);
        double dy = (i - kernel_center) * sin(angle);
        double distance = sqrt(dx * dx + dy * dy);
        kernel[i] = exp(-distance * distance / 2);  // ガウシアンカーネル
    }

    // 入力画像の端を重複させて折り返す
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight = 0.0;

            // カーネルを適用
            for (int ky = -kernel_center; ky <= kernel_center; ky++) {
                for (int kx = -kernel_center; kx <= kernel_center; kx++) {
                    int ky_abs = abs(ky);
                    int kx_abs = abs(kx);
                    if (ky_abs <= kernel_center && kx_abs <= kernel_center) {
                        int ny = y + ky;
                        int nx = x + kx;
                        // 端の処理: 入力画像の端を重複させて折り返す
                        ny = (ny < 0) ? -ny : (ny >= h ? 2 * h - ny - 1 : ny);
                        nx = (nx < 0) ? -nx : (nx >= w ? 2 * w - nx - 1 : nx);
                        sum += in[ny * w + nx] * kernel[ky_abs * (kernel_length + 1) + kx_abs];
                        weight += kernel[ky_abs * (kernel_length + 1) + kx_abs];
                    }
                }
            }

            // 結果を出力画像に格納
            out[y * w + x] = sum / weight;
        }
    }
}
