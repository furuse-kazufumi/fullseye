#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の画素を複製するためのパディング
    // 左右の端の画素を複製
    for (int y = 0; y < h; ++y) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 2];
    }

    // 上下の端の画素を複製
    for (int x = 0; x < w; ++x) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 2) * w + x];
    }

    // 中央の画素を処理
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double sum = 0.0;
            int count = 0;

            // ANGLE 方向のガウシアンフィルタリング
            for (int dy = -4; dy <= 4; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    double weight = exp(-0.5 * (dy * dy / (a * a) + dx * dx / (b * b)));
                    sum += in[ny * w + nx] * weight;
                    count += weight;
                }
            }

            out[y * w + x] = sum / count;
        }
    }
}
