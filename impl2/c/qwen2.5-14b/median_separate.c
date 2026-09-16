#include <stdlib.h>
#include <string.h>
#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3; // 初期値
    if (a < 0.25) {
        window_size = 3;
    } else if (a < 0.5) {
        window_size = 5;
    } else if (a < 0.75) {
        window_size = 7;
    } else {
        window_size = 9;
    }

    // 窓サイズが奇数であることを確認
    if (window_size % 2 == 0) {
        window_size++;
    }

    // メディアンフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセル値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内のピクセルを取得
            for (int dy = -window_size / 2; dy <= window_size / 2; dy++) {
                for (int dx = -window_size / 2; dx <= window_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 反射境界条件
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内のピクセル値をソート
            qsort(window, window_size * window_size, sizeof(double), compare);

            // 中央のピクセル値を出力画像に設定
            out[y * w + x] = window[window_size * window_size / 2];
        }
    }
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
