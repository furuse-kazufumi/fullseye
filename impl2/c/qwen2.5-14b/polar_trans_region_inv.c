#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。
    (void)a;
    (void)b;

    // 出力画像の高さと幅を計算
    int output_size = (int) sqrt(h * h + w * w);
    int output_h = output_size;
    int output_w = output_size;

    // 出力画像の初期化
    for (int y = 0; y < output_h; ++y) {
        for (int x = 0; x < output_w; ++x) {
            out[y * output_w + x] = 0.0;
        }
    }

    // 入力画像の各画素を処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] == 1.0) {
                // 枠の中心座標
                int center_x = (w - 1) / 2;
                int center_y = (h - 1) / 2;

                // 枠の半径
                int radius = (int) sqrt((w / 2) * (w / 2) + (h / 2) * (h / 2));

                // 極座標からデカルト座標への変換
                double theta = atan2(y - center_y, x - center_x);
                double r = sqrt((y - center_y) * (y - center_y) + (x - center_x) * (x - center_x));

                // デカルト座標系での座標を計算
                int out_x = (int) (center_x + r * cos(theta));
                int out_y = (int) (center_y + r * sin(theta));

                // 出力画像の範囲内に収まるかチェック
                if (out_x >= 0 && out_x < output_w && out_y >= 0 && out_y < output_h) {
                    out[out_y * output_w + out_x] = 1.0;
                }
            }
        }
    }
}
