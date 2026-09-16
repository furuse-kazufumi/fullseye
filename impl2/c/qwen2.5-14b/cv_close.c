#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    if (se_size < 3) se_size = 3; // 最小サイズは 3x3
    if (se_size > 9) se_size = 9; // 最大サイズは 9x9

    // 中心座標を計算
    int se_center = (se_size - 1) / 2;

    // 出力画像を入力画像と同じにする
    memcpy(out, in, h * w * sizeof(double));

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = in[y * w + x];
            for (int dy = -se_center; dy <= se_center; dy++) {
                for (int dx = -se_center; dx <= se_center; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, in[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = max_val;
        }
    }

    // 収縮処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = out[y * w + x];
            for (int dy = -se_center; dy <= se_center; dy++) {
                for (int dx = -se_center; dx <= se_center; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, out[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }
}
