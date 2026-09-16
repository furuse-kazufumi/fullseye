#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓サイズの決定
    int window_size = 3 + (int)(a * 3); // a は [0, 1] の範囲で、窓サイズは 3/5/7/9 の 4 段階に変化
    int half_window = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 中央値フィルタの適用
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
                    // 端の処理: 画像の端を重複させて折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    window[window_index++] = in[ny * w + nx];
                }
            }

            // 窓内の画素値をソート
            qsort(window, window_size * window_size, sizeof(double), (int (*)(const void *, const void *))compare);

            // 中央値を計算
            int median_index = window_size * window_size / 2;
            double median_value = window[median_index];

            // 出力画像に中央値を設定
            out[y * w + x] = median_value;
        }
    }
}

// qsort の比較関数
int compare(const void *a, const void *b) {
    double diff = *(double *)a - *(double *)b;
    if (diff < 0) return -1;
    if (diff > 0) return 1;
    return 0;
}
