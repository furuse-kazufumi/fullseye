#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は構造要素の一辺を 3,5,7,9 に変更する。
    int kernel_size = (int)(a * 4 + 1); // a が 0.1 から 0.9 の範囲で動くと、kernel_size は 3, 5, 7, 9 に変化する。
    if (kernel_size < 3) kernel_size = 3; // 最小値は 3 に保つ。
    if (kernel_size > 9) kernel_size = 9; // 最大値は 9 に保つ。

    // クロージングと元の画像の差分を計算する。
    // 画像の端は、境界値を用いて補間する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double min_value = in[y * w + x];
            int start_y = y - kernel_size / 2;
            int end_y = y + kernel_size / 2 + 1;
            int start_x = x - kernel_size / 2;
            int end_x = x + kernel_size / 2 + 1;

            // 結果を正規化するための最大値を計算
            double max_value = 0.0;
            for (int ky = start_y; ky < end_y; ++ky) {
                for (int kx = start_x; kx < end_x; ++kx) {
                    int iy = ky;
                    int ix = kx;
                    if (iy < 0) iy = 0;
                    if (iy >= h) iy = h - 1;
                    if (ix < 0) ix = 0;
                    if (ix >= w) ix = w - 1;
                    double value = in[iy * w + ix];
                    if (value > max_value) max_value = value;
                    if (value < min_value) min_value = value;
                }
            }
            out[y * w + x] = (max_value - min_value) / max_value; // 正規化
        }
    }
}
