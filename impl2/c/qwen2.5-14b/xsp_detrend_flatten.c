#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない

    // 各行の線形回帰成分を計算
    for (int y = 0; y < h; ++y) {
        double sum_x = 0.0;
        double sum_y = 0.0;
        double sum_xx = 0.0;
        double sum_xy = 0.0;
        for (int x = 0; x < w; ++x) {
            double value = in[y * w + x];
            sum_x += x;
            sum_y += value;
            sum_xx += x * x;
            sum_xy += x * value;
        }
        double denominator = w * sum_xx - sum_x * sum_x;
        double m = (w * sum_xy - sum_x * sum_y) / denominator;
        double c = (sum_xx * sum_y - sum_x * sum_xy) / denominator;

        // 各行の線形回帰成分を差し引く
        for (int x = 0; x < w; ++x) {
            double value = in[y * w + x];
            out[y * w + x] = value - (m * x + c);
        }
    }

    // 各列の線形回帰成分を計算
    for (int x = 0; x < w; ++x) {
        double sum_y = 0.0;
        double sum_yy = 0.0;
        double sum_yx = 0.0;
        for (int y = 0; y < h; ++y) {
            double value = out[y * w + x];
            sum_y += y;
            sum_yy += y * y;
            sum_yx += y * value;
        }
        double denominator = h * sum_yy - sum_y * sum_y;
        double m = (h * sum_yx - sum_y * sum_yy) / denominator;
        double c = (sum_yy * sum_y - sum_y * sum_yx) / denominator;

        // 各列の線形回帰成分を差し引く
        for (int y = 0; y < h; ++y) {
            double value = out[y * w + x];
            out[y * w + x] = value - (m * y + c);
        }
    }
}
