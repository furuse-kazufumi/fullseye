#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 回転角とせん断量をラジアンに変換
    double rad_a = a * M_PI / 180.0; // 0.5 は 20° に相当
    double shear = (b - 0.5) * 0.4; // 0.5 は 0 に相当

    // 画像の中心座標
    double cx = (w - 1) / 2.0;
    double cy = (h - 1) / 2.0;

    // アフィン変換行列
    double cos_a = cos(rad_a);
    double sin_a = sin(rad_a);
    double affine[6] = {
        cos_a, sin_a, -sin_a * cy - cos_a * cx,
        -sin_a, cos_a, sin_a * cx - cos_a * cy
    };

    // 画像の各ピクセルに対してアフィン変換を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 変換後の座標を計算
            double tx = x * cos_a + y * sin_a + affine[2];
            double ty = -x * sin_a + y * cos_a + affine[5];

            // 座標を整数に変換
            int ix = (int)floor(tx + 0.5);
            int iy = (int)floor(ty + 0.5);

            // 鏡映境界処理
            if (ix < 0) ix = -ix;
            if (ix >= w) ix = 2 * w - 2 - ix;
            if (iy < 0) iy = -iy;
            if (iy >= h) iy = 2 * h - 2 - iy;

            // 出力画像に値を設定
            out[y * w + x] = in[iy * w + ix];
        }
    }
}
