#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 回転角とシアー量を計算
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0; // -20°〜+20°
    double shear = (b - 0.5) * 0.5; // -0.25〜+0.25

    // 画像の端を鏡映で埋める
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // アフィン変換後の座標を計算
            double x_new = x * cos(angle) - y * sin(angle) + shear * y;
            double y_new = x * sin(angle) + y * cos(angle);

            // 座標を画像の範囲内に収める
            int x_new_clipped = (int)round(x_new);
            int y_new_clipped = (int)round(y_new);
            if (x_new_clipped < 0) x_new_clipped = -x_new_clipped;
            if (x_new_clipped >= w) x_new_clipped = 2 * w - 2 - x_new_clipped;
            if (y_new_clipped < 0) y_new_clipped = -y_new_clipped;
            if (y_new_clipped >= h) y_new_clipped = 2 * h - 2 - y_new_clipped;

            // 出力画像に値を設定
            out[y * w + x] = in[y_new_clipped * w + x_new_clipped];
        }
    }
}
