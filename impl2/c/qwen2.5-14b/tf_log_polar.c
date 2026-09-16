#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の中心座標
    int center_x = w / 2;
    int center_y = h / 2;

    // 出力画像のサイズを計算
    int out_h = h; // 出力画像の高さは入力画像の高さと同じ
    int out_w = w; // 出力画像の幅も同様

    // 出力画像の各ピクセルに対して
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            // ログ極座標系での座標を計算
            double log_radius = log(sqrt(pow(x - center_x, 2) + pow(y - center_y, 2)) + 1);
            double angle = atan2(y - center_y, x - center_x);

            // 角度を 0 から 2π の範囲に正規化
            angle = fmod(angle + M_PI, 2 * M_PI) - M_PI;

            // スケーリングと回転を適用
            log_radius = log_radius * a + b;

            // ログ極座標系の座標を直交座標系に変換
            int src_x = center_x + (int)(exp(log_radius) * cos(angle));
            int src_y = center_y + (int)(exp(log_radius) * sin(angle));

            // 出力画像の座標を計算
            int out_x = (int)((angle + M_PI) / (2 * M_PI) * out_w);
            int out_y = (int)(log_radius);

            // 出力画像の座標が有効範囲内であることを確認
            if (src_x >= 0 && src_x < w && src_y >= 0 && src_y < h) {
                // 出力画像の座標が有効範囲内である場合、入力画像の値をコピー
                out[out_y * out_w + out_x] = in[src_y * w + src_x];
            } else {
                // 出力画像の座標が有効範囲外である場合、出力画像の値を 0 に設定
                out[out_y * out_w + out_x] = 0;
            }
        }
    }
}
