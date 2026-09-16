#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径の計算
    int radius = (int)(1 + a * 4);
    if (radius < 1) radius = 1; // 半径は最小 1 とする
    if (radius > 5) radius = 5; // 半径は最大 5 とする

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 等方閉じ処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                // 入力画素が 1 の場合、周囲の画素も考慮して処理
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の範囲外は無視
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }
}
