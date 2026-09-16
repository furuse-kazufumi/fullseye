#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 深さしきい値 h の計算
    double h_threshold = 0.05 + 0.3 * a;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各ピクセルに対して処理を行う
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 8近傍のピクセルの値を取得
            double center = in[y * w + x];
            double north = in[(y - 1) * w + x];
            double south = in[(y + 1) * w + x];
            double east = in[y * w + x + 1];
            double west = in[y * w + x - 1];
            double ne = in[(y - 1) * w + x + 1];
            double nw = in[(y - 1) * w + x - 1];
            double se = in[(y + 1) * w + x + 1];
            double sw = in[(y + 1) * w + x - 1];

            // 8近傍の最小値を取得
            double min_neighbor = fmin(fmin(fmin(fmin(north, south), fmin(east, west)), fmin(fmin(ne, nw), fmin(se, sw)));

            // 深さしきい値 h を超える極小点をマーク
            if (center < min_neighbor && center - min_neighbor < h_threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
