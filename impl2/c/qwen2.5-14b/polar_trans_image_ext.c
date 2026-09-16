#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。極座標変換の中心は画像の中心固定。
    // 半径の最大値は min(h, w) / 2。角度範囲は 0 から 2 * PI。
    // 画像の端を線形補間で埋める。

    int center_x = w / 2;
    int center_y = h / 2;
    double max_radius = (double)MIN(h, w) / 2.0;
    double angle_step = 2.0 * M_PI / (w - 1); // 画像の幅で角度を分割

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 枠外のピクセルは線形補間で埋める
            double radius = hypot((double)x - center_x, (double)y - center_y);
            double angle = atan2((double)y - center_y, (double)x - center_x);

            // 半径と角度を極座標の範囲にマッピング
            double mapped_radius = radius / max_radius * (w - 1) / 2.0;
            double mapped_angle = angle / (2.0 * M_PI) * (w - 1);

            // 枠外のピクセルを線形補間で埋める
            int src_x = (int)floor(mapped_angle);
            int src_y = (int)floor(mapped_radius);
            double dx = mapped_angle - src_x;
            double dy = mapped_radius - src_y;

            // 4 頂点の値を取得
            double v1 = bilinear_interpolation(in, h, w, center_x + src_x, center_y + src_y);
            double v2 = bilinear_interpolation(in, h, w, center_x + src_x + 1, center_y + src_y);
            double v3 = bilinear_interpolation(in, h, w, center_x + src_x, center_y + src_y + 1);
            double v4 = bilinear_interpolation(in, h, w, center_x + src_x + 1, center_y + src_y + 1);

            // 線形補間
            double interpolated_value = (1 - dx) * ((1 - dy) * v1 + dy * v3) + dx * ((1 - dy) * v2 + dy * v4);

            // 出力画像に書き込む
            out[y * w + x] = interpolated_value;
        }
    }
}

// 線形補間関数
double bilinear_interpolation(const double* img, int h, int w, int x, int y) {
    // 画像の端を 0 で埋める
    if (x < 0 || x >= w || y < 0 || y >= h) {
        return 0.0;
    }
    return img[y * w + x];
}
