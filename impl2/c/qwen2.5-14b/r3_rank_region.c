#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = (int)(3 + (a - 0.5) * 4); // a が 0.1 から 0.9 まで変化するとき、window_size は 3 から 7 まで変化する
    if (window_size < 3) window_size = 3; // 最小値 3
    if (window_size > 7) window_size = 7; // 最大値 7

    // 窓の半径
    int radius = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素について処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内の画素数をカウント
            int count = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の外側は背景(0)とみなす
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] > 0.5) {
                            count++;
                        }
                    }
                }
            }

            // 窓内の画素数が閾値を超えた場合、出力画像に 1 を設定
            int threshold = (int)(window_size * window_size * b);
            if (count >= threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
