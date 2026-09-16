#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は [0, 1] の範囲で、それぞれ横半径と縦半径のスケールを表す。
    // ここでは、a * w / 2 と b * h / 2 が楕円の半径となる。
    double rx = a * w / 2.0;
    double ry = b * h / 2.0;

    // 楕円の中心は画像の中心とする。
    double cx = w / 2.0;
    double cy = h / 2.0;

    // 画像の各ピクセルに対して、楕円内かどうかを判定する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 楕円の方程式 (x - cx)^2 / rx^2 + (y - cy)^2 / ry^2 <= 1 を使用する。
            double dx = x - cx;
            double dy = y - cy;
            double ellipse_eq = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry);

            // 楕円内なら 1.0、外なら 0.0 を出力する。
            out[y * w + x] = (ellipse_eq <= 1.0) ? 1.0 : 0.0;
        }
    }
}
