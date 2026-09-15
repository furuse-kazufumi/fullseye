#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 回転角 a は [-20°, +20°] の範囲にスケーリング
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0;
    // せん断量 b は [-0.5, +0.5] の範囲にスケーリング
    double shear = (b - 0.5) * 1.0;

    // アフィン変換行列の計算
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);
    double affine_matrix[6] = {
        cos_theta, -sin_theta, 0.0,
        sin_theta + shear, cos_theta, 0.0
    };

    // 画像の中心
    double cx = w / 2.0;
    double cy = h / 2.0;

    // 出力画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 変換前の座標を計算
            double x_in = (x - cx) * affine_matrix[0] + (y - cy) * affine_matrix[1] + cx;
            double y_in = (x - cx) * affine_matrix[3] + (y - cy) * affine_matrix[4] + cy;

            // 反射で境界外の値を処理
            if (x_in < 0) x_in = -x_in - 1;
            if (x_in >= w) x_in = 2 * w - x_in - 1;
            if (y_in < 0) y_in = -y_in - 1;
            if (y_in >= h) y_in = 2 * h - y_in - 1;

            // 双線形補間
            int x0 = (int)x_in;
            int y0 = (int)y_in;
            int x1 = x0 + 1;
            int y1 = y0 + 1;
            double wx = x_in - x0;
            double wy = y_in - y0;

            double v00 = in[y0 * w + x0];
            double v01 = in[y0 * w + x1];
            double v10 = in[y1 * w + x0];
            double v11 = in[y1 * w + x1];

            double interpolated_value = (1 - wx) * (1 - wy) * v00 +
                                        wx * (1 - wy) * v01 +
                                        (1 - wx) * wy * v10 +
                                        wx * wy * v11;

            out[y * w + x] = interpolated_value;
        }
    }
}
