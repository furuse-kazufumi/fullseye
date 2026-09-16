#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 楕円の中心座標
    double cx = w * 0.42;
    double cy = h * 0.30;

    // 楕円の半長軸と半短軸
    double semi_major_axis = w * 0.42;
    double semi_minor_axis = h * 0.30;

    // 開始角と終了角
    double start_angle = b * 2 * M_PI;
    double sweep_angle = 0.1 + a * (2 * M_PI - 0.1);
    double end_angle = start_angle + sweep_angle;

    // 出力を初期化
    memset(out, 0, h * w * sizeof(double));

    // 各ピクセルに対して楕円セクタ内かどうかを判定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 中心からの相対座標
            double dx = x - cx;
            double dy = y - cy;

            // 楕円の方程式に変換
            double ellipse_eq = (dx * dx) / (semi_major_axis * semi_major_axis) + (dy * dy) / (semi_minor_axis * semi_minor_axis);

            // 角度の計算
            double angle = atan2(dy, dx);
            if (angle < 0) {
                angle += 2 * M_PI;
            }

            // 角度が開始角と終了角の間にあり、かつ楕円内にいる場合
            if (ellipse_eq <= 1.0 && angle >= start_angle && angle <= end_angle) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
