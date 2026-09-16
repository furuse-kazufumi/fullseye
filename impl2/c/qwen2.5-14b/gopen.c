#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の一辺の長さを計算
    int k = (int)round(3 + 4 * a); // a は [0, 1] の範囲で、k は 3, 5, 7, 9 に段階的に変化する
    int k_half = k / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 侵食
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            for (int ky = -k_half; ky <= k_half; ky++) {
                for (int kx = -k_half; kx <= k_half; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }

    // 膨張
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = out[y * w + x];
            for (int ky = -k_half; ky <= k_half; ky++) {
                for (int kx = -k_half; kx <= k_half; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, out[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }
}
