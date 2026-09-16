#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを決定
    int kernel_size = (int)(a * 4 + 1); // つまみ a に基づいて 3, 5, 7, 9 のいずれかを決定
    if (kernel_size < 3) kernel_size = 3; // 最小値は 3
    if (kernel_size > 9) kernel_size = 9; // 最大値は 9

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // エッジ処理のためのパディング
    int pad = kernel_size / 2;
    int padded_h = h + 2 * pad;
    int padded_w = w + 2 * pad;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    memset(padded_in, 0, padded_h * padded_w * sizeof(double));

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + pad) * padded_w + (x + pad)] = in[y * w + x];
        }
    }

    // 収縮操作
    for (int y = pad; y < h + pad; y++) {
        for (int x = pad; x < w + pad; x++) {
            double min_val = padded_in[(y - pad) * padded_w + (x - pad)];
            for (int ky = -pad; ky <= pad; ky++) {
                for (int kx = -pad; kx <= pad; kx++) {
                    int ky_abs = abs(ky);
                    int kx_abs = abs(kx);
                    if (ky_abs <= pad && kx_abs <= pad) {
                        min_val = fmin(min_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                    }
                }
            }
            out[(y - pad) * w + (x - pad)] = min_val;
        }
    }

    // 膨張操作
    for (int y = pad; y < h + pad; y++) {
        for (int x = pad; x < w + pad; x++) {
            double max_val = padded_in[(y - pad) * padded_w + (x - pad)];
            for (int ky = -pad; ky <= pad; ky++) {
                for (int kx = -pad; kx <= pad; kx++) {
                    int ky_abs = abs(ky);
                    int kx_abs = abs(kx);
                    if (ky_abs <= pad && kx_abs <= pad) {
                        max_val = fmax(max_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                    }
                }
            }
            out[(y - pad) * w + (x - pad)] = max_val;
        }
    }

    // メモリ解放
    free(padded_in);
}
