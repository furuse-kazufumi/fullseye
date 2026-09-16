#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 回転角度をラジアンに変換
    double angle = (a - 0.5) * M_PI / 2.0; // -45°〜+45°の範囲に変換

    // 回転行列の計算
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);

    // 中心座標
    double center_x = (w - 1) / 2.0;
    double center_y = (h - 1) / 2.0;

    // 出力画像の各ピクセルに対する入力画像の座標を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 回転後の座標を計算
            double new_x = (x - center_x) * cos_theta - (y - center_y) * sin_theta + center_x;
            double new_y = (x - center_x) * sin_theta + (y - center_y) * cos_theta + center_y;

            // 反射法で枠外の部分を埋める
            int rx = (int)floor(new_x);
            int ry = (int)floor(new_y);
            if (rx < 0) rx = -rx;
            if (ry < 0) ry = -ry;
            if (rx >= w) rx = 2 * w - 2 - rx;
            if (ry >= h) ry = 2 * h - 2 - ry;

            // 出力画像に値を設定
            out[y * w + x] = in[ry * w + rx];
        }
    }
}
