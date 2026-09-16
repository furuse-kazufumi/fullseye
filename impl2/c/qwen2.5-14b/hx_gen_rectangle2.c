#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b の範囲を [0, 1] に制限
    a = fmax(0.0, fmin(1.0, a));
    b = fmax(0.0, fmin(1.0, b));

    // 半幅と半高さの計算
    double half_width = a * 0.5 * w;
    double half_height = a * 0.3 * h;

    // 回転角の計算
    double angle = b * M_PI;

    // 中心座標
    double center_x = (w - 1) / 2.0;
    double center_y = (h - 1) / 2.0;

    // 画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルの座標を中心座標からの相対座標に変換
            double rel_x = x - center_x;
            double rel_y = y - center_y;

            // 座標を回転
            double cos_theta = cos(angle);
            double sin_theta = sin(angle);
            double rotated_x = rel_x * cos_theta - rel_y * sin_theta;
            double rotated_y = rel_x * sin_theta + rel_y * cos_theta;

            // 回転後の座標が矩形内に収まっているか判定
            if (fabs(rotated_x) <= half_width && fabs(rotated_y) <= half_height) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
