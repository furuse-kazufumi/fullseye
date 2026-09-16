#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = 3 + 2 * (int)(a * 3);
    int radius = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 窓内のピクセルのカウント
            int count[256] = {0};
            int valid_count = 0;

            // 窓内のピクセルをカウント
            for (int dy = -radius; dy <= radius; ++dy) {
                for (int dx = -radius; dx <= radius; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の範囲外の場合はスキップ
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) continue;
                    int value = (int)(in[ny * w + nx] * 255.0);
                    count[value]++;
                    valid_count++;
                }
            }

            // 最頻値の計算
            int mode = -1;
            int max_count = 0;
            for (int i = 0; i < 256; ++i) {
                if (count[i] > max_count) {
                    max_count = count[i];
                    mode = i;
                }
            }

            // 最頻値を出力画像に設定
            out[y * w + x] = mode / 255.0;
        }
    }
}
