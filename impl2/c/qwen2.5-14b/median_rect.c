#include <stdlib.h>
#include <string.h>
#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの計算
    int k_a = (int)(a * 8 + 1); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    int k_b = (int)(b * 8 + 1); // 0.1 -> 3, 0.5 -> 5, 0.9 -> 9
    int k_a_half = k_a / 2;
    int k_b_half = k_b / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // メディアンフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 窓内のピクセル値を格納する配列
            double window[k_a * k_b];
            int window_index = 0;

            // 窓内のピクセルを取得
            for (int dy = -k_a_half; dy <= k_a_half; dy++) {
                for (int dx = -k_b_half; dx <= k_b_half; dx++) {
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

            // 窓内のピクセル値をソート
            qsort(window, k_a * k_b, sizeof(double), (int (*)(const void *, const void *))compare);

            // 中央のピクセル値を出力画像に設定
            out[y * w + x] = window[k_a * k_b / 2];
        }
    }
}

// 比較関数
int compare(const void *a, const void *b) {
    double diff = *(double *)a - *(double *)b;
    if (diff > 0) return 1;
    else if (diff < 0) return -1;
    else return 0;
}
