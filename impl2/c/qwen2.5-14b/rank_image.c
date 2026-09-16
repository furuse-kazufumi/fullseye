#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int window_size = (int)(a * 8 + 3); // 3, 5, 7, 9 に近似
    if (window_size % 2 == 0) {
        window_size++; // 窓サイズは奇数でなければならない
    }
    int half_window = window_size / 2;

    // パーセンタイルの計算
    int percentile = (int)(b * 90 + 5); // 5 から 95 に近似

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素について処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内の画素値を格納する配列
            double window[window_size * window_size];
            int window_index = 0;

            // 窓内の画素値を取得
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 端の処理: 入力画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内の画素値を昇順に並べ替え
            qsort(window, window_size * window_size, sizeof(double), compare);

            // 指定されたパーセンタイルの値を取得
            int index = (window_size * window_size - 1) * percentile / 100;
            out[y * w + x] = window[index];
        }
    }
}

// 比較関数
int compare(const void* a, const void* b) {
    return (*(double*)a - *(double*)b);
}
