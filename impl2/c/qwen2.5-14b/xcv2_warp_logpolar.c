#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 出力画像のサイズを計算
    int min_dim = (h < w) ? h : w;
    int out_h = min_dim / 2;
    int out_w = min_dim;

    // 出力画像の最大半径
    double max_radius = min_dim / 2.0;

    // 出力画像の各ピクセルに対する入力画像のピクセルの位置を計算
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            // 対数極座標から直交座標への変換
            double radius = exp((x - out_w / 2.0) / out_w * log(max_radius));
            double angle = (y - out_h / 2.0) / out_h * M_PI * 2.0;

            // 直交座標から入力画像のピクセル位置への変換
            double cx = radius * cos(angle) + w / 2.0;
            double cy = radius * sin(angle) + h / 2.0;

            // ピクセル位置を整数に丸める
            int ix = (int)round(cx);
            int iy = (int)round(cy);

            // ピクセル位置が画像の範囲内であることを確認
            if (ix >= 0 && ix < w && iy >= 0 && iy < h) {
                out[y * out_w + x] = in[iy * w + ix];
            } else {
                // 範囲外の場合は、境界値を出力として使用
                out[y * out_w + x] = 0.0;
            }
        }
    }
}
