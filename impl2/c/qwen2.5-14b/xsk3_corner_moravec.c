#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 1 + 2 * (int)(a * 2); // 1, 3, 5 のいずれか
    int half_window = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // データの範囲を [0,1] に正規化
    double min_val = 1.0;
    double max_val = 0.0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] < min_val) min_val = in[y * w + x];
            if (in[y * w + x] > max_val) max_val = in[y * w + x];
        }
    }
    double range = max_val - min_val;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            in[y * w + x] = (in[y * w + x] - min_val) / range;
        }
    }

    // モラベックコーナー検出
    double max_response = 0.0;
    for (int y = half_window; y < h - half_window; y++) {
        for (int x = half_window; x < w - half_window; x++) {
            double response = 0.0;
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    if (dx == 0 && dy == 0) continue;
                    double I1 = in[(y + dy) * w + (x + dx)];
                    double I2 = in[(y - dy) * w + (x - dx)];
                    response += pow(I1 - I2, 2);
                }
            }
            out[y * w + x] = response;
            if (response > max_response) max_response = response;
        }
    }

    // 正規化
    if (max_response > 0.0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] /= max_response;
            }
        }
    }
}
