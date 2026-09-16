#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズを決定。a が 0.25, 0.5, 0.75 のときに窓サイズが切り替わる。
    int window_size = (a < 0.25) ? 3 : (a < 0.5) ? 5 : (a < 0.75) ? 7 : 9;
    int half_window = window_size / 2;

    // メディアンフィルタリングのための配列
    double window[window_size * window_size];
    int window_index = 0;

    // 出力画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセルを取得
            window_index = 0;
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 端の処理: 端画素を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内のピクセルをソート
            qsort(window, window_size * window_size, sizeof(double), (int (*)(const void *, const void *))compare);

            // 中央値を出力画像に設定
            out[y * w + x] = window[(window_size * window_size - 1) / 2];
        }
    }
}

// 比較関数
int compare(const void *a, const void *b) {
    return (*(double*)a > *(double*)b) - (*(double*)a < *(double*)b);
}
