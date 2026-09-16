#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 倍率の計算
    double scale = 0.7 + 0.6 * a;
    // 中心座標の計算
    int center_x = w / 2;
    int center_y = h / 2;
    // 出力画像のサイズ計算
    int out_h = (int)(h * scale);
    int out_w = (int)(w * scale);
    // 中心座標の調整
    int center_x_out = out_w / 2;
    int center_y_out = out_h / 2;

    // 出力画像の初期化
    for (int y = 0; y < out_h; y++) {
        for (int x = 0; x < out_w; x++) {
            out[y * out_w + x] = 0.0;
        }
    }

    // ミラーリングとリサンプリング
    for (int y_out = 0; y_out < out_h; y_out++) {
        for (int x_out = 0; x_out < out_w; x_out++) {
            // 出力座標から入力座標への変換
            double x_in = (x_out - center_x_out) / scale + center_x;
            double y_in = (y_out - center_y_out) / scale + center_y;

            // ミラーリング
            int x_mirror = (int)floor(x_in);
            int y_mirror = (int)floor(y_in);
            if (x_mirror < 0) x_mirror = -x_mirror;
            if (y_mirror < 0) y_mirror = -y_mirror;
            if (x_mirror >= w) x_mirror = 2 * w - 2 - x_mirror;
            if (y_mirror >= h) y_mirror = 2 * h - 2 - y_mirror;

            // バイリニア補間
            double x0 = floor(x_in);
            double y0 = floor(y_in);
            double x1 = x0 + 1;
            double y1 = y0 + 1;
            double dx = x_in - x0;
            double dy = y_in - y0;

            double v00 = in[y0 * w + x0];
            double v01 = in[y0 * w + x1];
            double v10 = in[y1 * w + x0];
            double v11 = in[y1 * w + x1];

            double value = (1 - dx) * (1 - dy) * v00 + dx * (1 - dy) * v01 + (1 - dx) * dy * v10 + dx * dy * v11;

            // しきい値処理
            out[y_out * out_w + x_out] = (value >= 0.5) ? 1.0 : 0.0;
        }
    }
}
