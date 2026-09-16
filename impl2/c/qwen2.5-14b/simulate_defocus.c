#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓幅の決定
    int window_size = 3 + (int)(a * 3); // a が 0.1 から 0.9 の範囲で、window_size は 3 から 9 の範囲となる
    if (window_size % 2 == 0) {
        window_size++; // 窓サイズは奇数でなければならない
    }

    // 中心窓サイズの半分
    int half_window = window_size / 2;

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 平均フィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // 窓内の各ピクセルに対して
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // 端の処理: 入力画像の端を折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;

                    sum += in[ny * w + nx];
                    count++;
                }
            }

            // 平均値の計算
            out[y * w + x] = sum / count;
        }
    }
}
