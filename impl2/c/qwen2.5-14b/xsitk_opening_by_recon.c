#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の半径を計算
    int radius = 1 + (int)(a * 4); // 1 から 5 までの整数値

    // 出力画像をクリア
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 收縮 (Erosion)
    for (int i = 0; i < radius; i++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double min_val = in[y * w + x];
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            min_val = fmin(min_val, in[ny * w + nx]);
                        }
                    }
                }
                out[y * w + x] = min_val;
            }
        }
    }

    // 膨張 (Dilation) と再構成
    for (int i = 0; i < radius; i++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double max_val = out[y * w + x];
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            max_val = fmax(max_val, out[ny * w + nx]);
                        }
                    }
                }
                out[y * w + x] = max_val;
            }
        }
    }

    // 出力を [0,1] の範囲にクリップ
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = fmin(fmax(out[y * w + x], 0.0), 1.0);
        }
    }
}
