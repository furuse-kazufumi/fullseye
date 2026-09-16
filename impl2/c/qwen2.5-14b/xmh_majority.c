#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 2 * (int)(1 + a * 4) + 1;
    int half_window = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素に対して多数決フィルタリングを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            // 近傍領域の画素をカウント
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を避ける
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 1.0) {
                            count++;
                        }
                    }
                }
            }
            // 過半数の画素が 1 である場合、出力画像の該当画素を 1 に設定
            if (count > (window_size * window_size) / 2) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
