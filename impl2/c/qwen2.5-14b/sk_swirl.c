#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の中心座標
    int center_x = w / 2;
    int center_y = h / 2;
    // 渦巻きの強さと半径
    double strength = 1 + 4 * a;
    double radius = 30;

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルの中心からの距離と角度
            double dx = x - center_x;
            double dy = y - center_y;
            double distance = sqrt(dx * dx + dy * dy);
            double angle = atan2(dy, dx);

            // 渦巻きの効果を適用
            double swirl_angle = angle + strength * sin(distance / radius);
            double swirl_distance = distance * exp(-distance / radius);

            // 新しい座標を計算
            int new_x = center_x + swirl_distance * cos(swirl_angle);
            int new_y = center_y + swirl_distance * sin(swirl_angle);

            // 新しい座標が画像の範囲外の場合、BORDER_REFLECT_101 モードで対応
            if (new_x < 0) new_x = -new_x;
            if (new_x >= w) new_x = 2 * w - 2 - new_x;
            if (new_y < 0) new_y = -new_y;
            if (new_y >= h) new_y = 2 * h - 2 - new_y;

            // 出力画像に値を設定
            out[y * w + x] = in[new_y * w + new_x];
        }
    }
}
