#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a: 0.0 から 1.0 の間で回転角度を決定。1.0 は 20°、0.0 は -20°。
    // b: 0.0 から 1.0 の間でせん断量を決定。
    // 画像の端は反射で埋める。

    double rotation_angle = a * 40.0 - 20.0; // 回転角度の計算
    double shear = b * 2.0 - 1.0; // せん断量の計算

    // アフィン変換行列の定義
    double cos_theta = cos(rotation_angle * M_PI / 180.0);
    double sin_theta = sin(rotation_angle * M_PI / 180.0);
    double affine_matrix[6] = {cos_theta, -sin_theta * shear, sin_theta, cos_theta, 0, 0};

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // アフィン変換の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double new_x = x * affine_matrix[0] + y * affine_matrix[1] + affine_matrix[2];
            double new_y = x * affine_matrix[3] + y * affine_matrix[4] + affine_matrix[5];

            // 反射で枠外を埋める
            if (new_x < 0) new_x = -new_x;
            if (new_y < 0) new_y = -new_y;
            if (new_x >= w) new_x = 2 * w - 2 - new_x;
            if (new_y >= h) new_y = 2 * h - 2 - new_y;

            // バイリニア補間
            int x1 = floor(new_x);
            int y1 = floor(new_y);
            int x2 = x1 + 1;
            int y2 = y1 + 1;
            double dx = new_x - x1;
            double dy = new_y - y1;

            double value = 0.0;
            if (x1 >= 0 && x1 < w && y1 >= 0 && y1 < h) {
                value += (1 - dx) * (1 - dy) * in[y1 * w + x1];
            }
            if (x2 >= 0 && x2 < w && y1 >= 0 && y1 < h) {
                value += dx * (1 - dy) * in[y1 * w + x2];
            }
            if (x1 >= 0 && x1 < w && y2 >= 0 && y2 < h) {
                value += (1 - dx) * dy * in[y2 * w + x1];
            }
            if (x2 >= 0 && x2 < w && y2 >= 0 && y2 < h) {
                value += dx * dy * in[y2 * w + x2];
            }

            out[y * w + x] = value;
        }
    }
}
