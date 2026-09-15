#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 回転角を -20° から +20° にマッピング
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0;
    // せん断量を -0.2 から +0.2 にマッピング
    double shear = (b - 0.5) * 0.4;

    // 回転行列の計算
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);

    // 画像の中心
    double cx = w / 2.0;
    double cy = h / 2.0;

    // 出力画像の各ピクセルに対して
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 逆変換を適用
            double x_prime = (x - cx) * cos_theta + (y - cy) * sin_theta + cx;
            double y_prime = (x - cx) * (-sin_theta) + (y - cy) * cos_theta + cy;

            // せん断を適用
            x_prime += shear * y_prime;

            // 境界外アクセスを防ぐために reflect で境界を処理
            if (x_prime < 0) x_prime = -x_prime;
            if (x_prime >= w) x_prime = 2 * w - x_prime - 1;
            if (y_prime < 0) y_prime = -y_prime;
            if (y_prime >= h) y_prime = 2 * h - y_prime - 1;

            // 双線形補間
            int x0 = (int)x_prime;
            int y0 = (int)y_prime;
            int x1 = x0 + 1;
            int y1 = y0 + 1;

            double wx = x_prime - x0;
            double wy = y_prime - y0;

            double v00 = in[y0 * w + x0];
            double v01 = (x1 < w) ? in[y0 * w + x1] : v00;
            double v10 = (y1 < h) ? in[y1 * w + x0] : v00;
            double v11 = (y1 < h && x1 < w) ? in[y1 * w + x1] : v00;

            double interpolated_value = (1 - wx) * (1 - wy) * v00 +
                                        wx * (1 - wy) * v01 +
                                        (1 - wx) * wy * v10 +
                                        wx * wy * v11;

            // [0, 1] にクリッピング
            if (interpolated_value < 0) interpolated_value = 0;
            if (interpolated_value > 1) interpolated_value = 1;

            out[y * w + x] = interpolated_value;
        }
    }
}
