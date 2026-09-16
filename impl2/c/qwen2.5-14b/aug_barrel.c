#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータの初期化
    double k = 0.6 * a;
    double b_value = b < 0.5 ? b : 1.0 - b; // Barrel distortion if b < 0.5, otherwise pincushion

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルの中心座標を計算
            double cx = (x + 0.5) / w;
            double cy = (y + 0.5) / h;

            // ピクセルの径方向距離を計算
            double r = sqrt(cx * cx + cy * cy);

            // 径方向の歪みを適用
            double r_src = r * (1.0 + k * r * r);

            // 歪んだ座標を元の座標に逆写像
            double x_src = r_src * cx / r;
            double y_src = r_src * cy / r;

            // 逆写像された座標を画像の範囲に正規化
            x_src = (x_src + 0.5) * w;
            y_src = (y_src + 0.5) * h;

            // 反射境界条件を適用
            if (x_src < 0) x_src = -x_src;
            if (x_src >= w) x_src = 2 * w - 2 - x_src;
            if (y_src < 0) y_src = -y_src;
            if (y_src >= h) y_src = 2 * h - 2 - y_src;

            // 反射境界条件を適用した座標を整数に丸める
            int x0 = (int)floor(x_src);
            int y0 = (int)floor(y_src);
            int x1 = x0 + 1;
            int y1 = y0 + 1;

            // ビリニア補間を適用
            double dx = x_src - x0;
            double dy = y_src - y0;
            double w00 = (1 - dx) * (1 - dy);
            double w01 = (1 - dx) * dy;
            double w10 = dx * (1 - dy);
            double w11 = dx * dy;

            // 出力画像のピクセル値を計算
            double out_value = w00 * in[y0 * w + x0] + w01 * in[y1 * w + x0] + w10 * in[y0 * w + x1] + w11 * in[y1 * w + x1];

            // 出力画像に値を設定
            out[y * w + x] = out_value;
        }
    }
}
