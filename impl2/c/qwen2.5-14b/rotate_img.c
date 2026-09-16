#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の中心座標
    double center_x = (w - 1) / 2.0;
    double center_y = (h - 1) / 2.0;

    // 回転角度の計算
    double angle = -M_PI / 4 + M_PI / 2 * a; // -45° + 90°·a

    // 鏡映モードで枠外を埋めるための補間関数
    // ここでは、回転で枠外に出た画素は鏡映で補完する。
    // つまり、回転の結果、画像の四隅に元画像が折り返して写り込む。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 回転後の座標を計算
            double new_x = (x - center_x) * cos(angle) - (y - center_y) * sin(angle) + center_x;
            double new_y = (x - center_x) * sin(angle) + (y - center_y) * cos(angle) + center_y;

            // 座標を整数に変換
            int int_x = (int)floor(new_x);
            int int_y = (int)floor(new_y);

            // 鏡映補完
            if (int_x < 0) int_x = -int_x;
            if (int_y < 0) int_y = -int_y;
            if (int_x >= w) int_x = 2 * w - 2 - int_x;
            if (int_y >= h) int_y = 2 * h - 2 - int_y;

            // 出力画像に値を設定
            out[y * w + x] = in[int_y * w + int_x];
        }
    }
}
