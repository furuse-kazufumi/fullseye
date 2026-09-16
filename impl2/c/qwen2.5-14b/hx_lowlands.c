#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int size = 3 + (int)(a * 6); // 窓の一辺は 3 から 9 画素
    int half_size = size / 2;

    // 画像の平均値を計算
    double sum = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            sum += in[y * w + x];
        }
    }
    double mean = sum / (h * w);

    // マイナーフィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double mn = in[y * w + x];
            for (int dy = -half_size; dy <= half_size; dy++) {
                for (int dx = -half_size; dx <= half_size; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] < mn) {
                            mn = in[ny * w + nx];
                        }
                    }
                }
            }
            // 出力の計算
            if (in[y * w + x] <= mn + 1e-6 && in[y * w + x] < mean) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
