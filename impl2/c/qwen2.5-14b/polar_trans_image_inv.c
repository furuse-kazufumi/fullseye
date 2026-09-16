#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。中心と半径は画像サイズから自動的に決まる。
    // 中心は (w/2, h/2)、半径は min(w, h) / 2。
    int center_x = w / 2;
    int center_y = h / 2;
    int radius = (w < h) ? w / 2 : h / 2;

    // 出力画像の各ピクセルに対して、極座標から直交座標への逆変換を行う。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 枠外のピクセルは 0 で埋める。
            if (hypot(x - center_x, y - center_y) > radius) {
                out[y * w + x] = 0;
                continue;
            }

            // 極座標から直交座標への逆変換。
            double r = hypot(x - center_x, y - center_y);
            double theta = atan2(y - center_y, x - center_x);
            int src_x = center_x + r * cos(theta);
            int src_y = center_y + r * sin(theta);

            // 出力画像の範囲内に収まるかチェック。
            if (src_x >= 0 && src_x < w && src_y >= 0 && src_y < h) {
                out[y * w + x] = in[src_y * w + src_x];
            } else {
                // 枠外のピクセルは 0 で埋める。
                out[y * w + x] = 0;
            }
        }
    }
}
