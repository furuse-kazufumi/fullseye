#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数の計算
    double c = 0.05 + 0.4 * a;  // 円環の中心半径
    double half = 0.03 + 0.15 * b;  // 半幅
    double min_radius = c - half;  // 内半径
    double max_radius = c + half;  // 外半径

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 正規化周波数半径 r の計算
            double r = sqrt(((x - w / 2.0) * (x - w / 2.0) + (y - h / 2.0) * (y - h / 2.0)) / (w * h));
            // バンドフィルタの適用
            out[y * w + x] = (r >= min_radius && r <= max_radius) ? 1.0 : 0.0;
        }
    }
}
