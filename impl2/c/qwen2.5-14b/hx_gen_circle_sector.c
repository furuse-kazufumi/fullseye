#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 固定半径の計算
    int min_dim = h < w ? h : w;
    double radius = 0.42 * min_dim;
    double center_x = (w - 1) / 2.0;
    double center_y = (h - 1) / 2.0;

    // 扫引角と开始角の計算
    double sweep = 0.1 + a * (2 * M_PI - 0.1);
    double start = b * 2 * M_PI;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 圆心到每个像素的距离和角度
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = x - center_x;
            double dy = y - center_y;
            double distance = sqrt(dx * dx + dy * dy);
            double angle = atan2(dy, dx);

            // 角度を0〜2πの範囲に正規化
            while (angle < 0) angle += 2 * M_PI;
            while (angle > 2 * M_PI) angle -= 2 * M_PI;

            // 判断条件
            if (distance <= radius && ((angle - start) - floor((angle - start) / (2 * M_PI)) * (2 * M_PI)) <= sweep) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
