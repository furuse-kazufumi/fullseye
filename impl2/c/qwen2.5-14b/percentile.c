#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(3 + 2 * floor(2 * a));
    int half_window = window_size / 2;

    // パーセンタイルの計算
    int percentile = (int)(5 + 90 * b);

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // パーセンタイルフィルタリングの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセル値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内のピクセル値を取得
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int sy = y + dy;
                    int sx = x + dx;
                    // 反射境界条件
                    if (sy < 0) sy = -sy;
                    if (sy >= h) sy = 2 * h - sy - 1;
                    if (sx < 0) sx = -sx;
                    if (sx >= w) sx = 2 * w - sx - 1;
                    window[window_index++] = in[sy * w + sx];
                }
            }

            // 窓内のピクセル値をソート
            qsort(window, window_size * window_size, sizeof(double), compare);

            // パーセンタイル値を計算
            int index = (window_size * window_size - 1) * percentile / 100;
            out[y * w + x] = window[index];
        }
    }
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
