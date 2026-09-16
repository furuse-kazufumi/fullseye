#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 未使用のパラメータ b は無視する
    // 半径を min(h, w) の 10% から 50% の範囲で設定
    double radius = 0.1 + 0.4 * a;
    radius *= fmin(h, w) / 2.0;

    // 画像の中心座標
    double center_x = w / 2.0;
    double center_y = h / 2.0;

    // 各ピクセルに対して円内かどうかを判定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double dx = x - center_x;
            double dy = y - center_y;
            double distance = sqrt(dx * dx + dy * dy);

            // 円内なら 1.0、円外なら 0.0
            out[y * w + x] = (distance <= radius) ? 1.0 : 0.0;
        }
    }
}
