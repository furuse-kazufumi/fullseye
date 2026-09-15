#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a: 回転角を -20°〜+20° にスケーリング
    // b: シアー量をスケーリング
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0; // -20° to +20° in radians
    double shear = (b - 0.5) * 2.0; // -1.0 to +1.0

    // 回転行列の計算
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);

    // シアー行列の計算
    double shear_matrix[2][2] = {
        {1.0, shear},
        {0.0, 1.0}
    };

    // 出力画像を初期化
    memset(out, 0, sizeof(double) * h * w);

    // 各ピクセルに対してアフィン変換を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 元の座標を [-1, 1] の範囲に正規化
            double src_x = (2.0 * x - w) / w;
            double src_y = (2.0 * y - h) / h;

            // 回転を適用
            double rotated_x = src_x * cos_theta - src_y * sin_theta;
            double rotated_y = src_x * sin_theta + src_y * cos_theta;

            // シアーを適用
            double sheared_x = rotated_x * shear_matrix[0][0] + rotated_y * shear_matrix[0][1];
            double sheared_y = rotated_x * shear_matrix[1][0] + rotated_y * shear_matrix[1][1];

            // 正規化した座標を元の範囲に戻す
            double dst_x = sheared_x * w / 2.0 + w / 2.0;
            double dst_y = sheared_y * h / 2.0 + h / 2.0;

            // 近傍ピクセルの座標を計算
            int x0 = (int)floor(dst_x);
            int x1 = x0 + 1;
            int y0 = (int)floor(dst_y);
            int y1 = y0 + 1;

            // 重みを計算
            double wx = dst_x - x0;
            double wy = dst_y - y0;

            // フラミング処理: 境界外のピクセルは鏡映で埋める
            if (x0 < 0) x0 = -x0 - 1;
            if (x1 >= w) x1 = 2 * w - x1 - 1;
            if (y0 < 0) y0 = -y0 - 1;
            if (y1 >= h) y1 = 2 * h - y1 - 1;

            // 双線形補間
            double tl = in[y0 * w + x0];
            double tr = in[y0 * w + x1];
            double bl = in[y1 * w + x0];
            double br = in[y1 * w + x1];

            double top = tl * (1 - wx) + tr * wx;
            double bottom = bl * (1 - wx) + br * wx;
            double interpolated_value = top * (1 - wy) + bottom * wy;

            // 出力画像に代入
            out[y * w + x] = interpolated_value;
        }
    }
}
