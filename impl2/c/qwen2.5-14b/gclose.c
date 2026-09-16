#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを決定
    int kernel_size = (int)round(a * 4 + 1); // 3, 5, 7, 9 に切り替わる
    if (kernel_size % 2 == 0) kernel_size++; // 奇数に保つ

    // 辺の処理
    int padding = kernel_size / 2;
    int padded_h = h + 2 * padding;
    int padded_w = w + 2 * padding;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + padding) * padded_w + (x + padding)] = in[y * w + x];
        }
    }

    // パディング部分の初期化
    for (int y = 0; y < padding; y++) {
        for (int x = 0; x < padded_w; x++) {
            padded_in[y * padded_w + x] = padded_in[(y + h) * padded_w + x] = 0.0;
        }
    }

    // 膨張処理
    for (int y = padding; y < padded_h - padding; y++) {
        for (int x = padding; x < padded_w - padding; x++) {
            double max_val = padded_in[(y - padding) * padded_w + (x - padding)];
            for (int ky = -padding; ky <= padding; ky++) {
                for (int kx = -padding; kx <= padding; kx++) {
                    max_val = fmax(max_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                }
            }
            padded_in[y * padded_w + x] = max_val;
        }
    }

    // 侵食処理
    for (int y = padding; y < padded_h - padding; y++) {
        for (int x = padding; x < padded_w - padding; x++) {
            double min_val = padded_in[(y - padding) * padded_w + (x - padding)];
            for (int ky = -padding; ky <= padding; ky++) {
                for (int kx = -padding; kx <= padding; kx++) {
                    min_val = fmin(min_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                }
            }
            padded_in[y * padded_w + x] = min_val;
        }
    }

    // 出力画像へのコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = padded_in[(y + padding) * padded_w + (x + padding)];
        }
    }

    // メモリ解放
    free(padded_in);
}
