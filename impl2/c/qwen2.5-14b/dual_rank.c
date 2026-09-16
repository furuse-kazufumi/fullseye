#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3; // 初期値
    if (a <= 0.25) {
        window_size = 3;
    } else if (a <= 0.49) {
        window_size = 5;
    } else if (a <= 0.75) {
        window_size = 7;
    } else {
        window_size = 9;
    }

    // パーセンタイルの計算
    double percentile = b * 100.0;
    int rank = (int)round((window_size * window_size - 1) * percentile / 100.0);

    // 辺の処理: 反射境界条件
    int padded_h = h + window_size - 1;
    int padded_w = w + window_size - 1;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + (window_size - 1) / 2) * padded_w + (x + (window_size - 1) / 2)] = in[y * w + x];
        }
    }
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            if (y < (window_size - 1) / 2 || y >= h + (window_size - 1) / 2 || x < (window_size - 1) / 2 || x >= w + (window_size - 1) / 2) {
                int py = y < (window_size - 1) / 2 ? (window_size - 1) - (y - (window_size - 1) / 2) : h - (y - h - (window_size - 1) / 2);
                int px = x < (window_size - 1) / 2 ? (window_size - 1) - (x - (window_size - 1) / 2) : w - (x - w - (window_size - 1) / 2);
                padded_in[y * padded_w + x] = padded_in[py * padded_w + px];
            }
        }
    }

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double window[window_size * window_size];
            int index = 0;
            for (int dy = -((window_size - 1) / 2); dy <= ((window_size - 1) / 2); dy++) {
                for (int dx = -((window_size - 1) / 2); dx <= ((window_size - 1) / 2); dx++) {
                    window[index++] = padded_in[(y + dy + (window_size - 1) / 2) * padded_w + (x + dx + (window_size - 1) / 2)];
                }
            }
            qsort(window, window_size * window_size, sizeof(double), compare);
            out[y * w + x] = window[rank];
        }
    }

    free(padded_in);
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
