#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a は半径を決める。
    int r = 1 + (int)(a * 4);  // 半径の計算
    int kernel_size = 2 * r + 1;  // カーネルのサイズ

    // ゼロパディングされた領域の高さと幅
    int padded_h = h + 2 * r;
    int padded_w = w + 2 * r;

    // パディングされた領域の確保
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像をパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + r) * padded_w + (x + r)] = in[y * w + x];
        }
    }

    // パディングされた領域を初期化
    for (int y = 0; y < padded_h; y++) {
        for (int x = 0; x < padded_w; x++) {
            if (y < r || y >= padded_h - r || x < r || x >= padded_w - r) {
                padded_in[y * padded_w + x] = 0.0;  // パディング領域は 0 で初期化
            }
        }
    }

    // 膨張処理
    for (int y = r; y < padded_h - r; y++) {
        for (int x = r; x < padded_w - r; x++) {
            double max_val = 0.0;
            for (int ky = -r; ky <= r; ky++) {
                for (int kx = -r; kx <= r; kx++) {
                    max_val = fmax(max_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                }
            }
            padded_in[y * padded_w + x] = max_val;
        }
    }

    // 収縮処理
    for (int y = r; y < padded_h - r; y++) {
        for (int x = r; x < padded_w - r; x++) {
            double min_val = 1.0;
            for (int ky = -r; ky <= r; ky++) {
                for (int kx = -r; kx <= r; kx++) {
                    min_val = fmin(min_val, padded_in[(y + ky) * padded_w + (x + kx)]);
                }
            }
            padded_in[y * padded_w + x] = min_val;
        }
    }

    // 出力領域へのコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = padded_in[(y + r) * padded_w + (x + r)];
        }
    }

    // パディング領域の解放
    free(padded_in);
}
