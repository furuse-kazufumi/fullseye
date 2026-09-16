#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // メディアンフィルタのカーネルサイズを決定
    int kernel_size = (int)(a * 4);
    kernel_size = fmax(3, fmin(4, kernel_size)); // カーネルサイズは 3, 5, 7, 9 のいずれか
    int radius = (kernel_size - 1) / 2;

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 各ピクセルに対してメディアンフィルタを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // カーネル内のピクセルの値を格納する配列
            double kernel_values[kernel_size * kernel_size];
            int kernel_count = 0;

            // カーネル内の各ピクセルに対して
            for (int ky = -radius; ky <= radius; ++ky) {
                for (int kx = -radius; kx <= radius; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 画像の範囲外の場合は背景(0)とみなす
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        kernel_values[kernel_count++] = 0.0;
                    } else {
                        kernel_values[kernel_count++] = in[ny * w + nx];
                    }
                }
            }

            // カーネル内の値をソート
            qsort(kernel_values, kernel_count, sizeof(double), (int (*)(const void *, const void *))compare);

            // 中央値を出力画像に設定
            int median_index = kernel_count / 2;
            out[y * w + x] = kernel_values[median_index];
        }
    }
}

// 比較関数
int compare(const void *a, const void *b) {
    double diff = *(double *)a - *(double *)b;
    if (diff < 0) return -1;
    else if (diff > 0) return 1;
    else return 0;
}
