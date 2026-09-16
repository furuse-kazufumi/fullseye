#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 反射境界条件を適用するための補間画像の高さと幅
    int h_pad = h + 2;
    int w_pad = w + 2;
    double* in_padded = (double*)malloc(h_pad * w_pad * sizeof(double));
    double* out_padded = (double*)malloc(h_pad * w_pad * sizeof(double));

    // 入力画像を反射境界条件でパディング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            in_padded[(y + 1) * w_pad + (x + 1)] = in[y * w + x];
        }
    }
    for (int x = 1; x <= w; x++) {
        in_padded[0 * w_pad + x] = in_padded[1 * w_pad + x];
        in_padded[(h + 1) * w_pad + x] = in_padded[h * w_pad + x];
    }
    for (int y = 1; y <= h; y++) {
        in_padded[y * w_pad + 0] = in_padded[y * w_pad + 1];
        in_padded[y * w_pad + (w + 1)] = in_padded[y * w_pad + w];
    }
    in_padded[0 * w_pad + 0] = in_padded[1 * w_pad + 1];
    in_padded[0 * w_pad + (w + 1)] = in_padded[1 * w_pad + w];
    in_padded[(h + 1) * w_pad + 0] = in_padded[h * w_pad + 1];
    in_padded[(h + 1) * w_pad + (w + 1)] = in_padded[h * w_pad + w];

    // 反復回数を計算
    int iterations = (int)(a * 7 + 0.5); // 0.17, 0.33, 0.49, 0.67, 0.83, 0.99 に対応する 1, 2, 3, 4, 5, 6, 7
    if (iterations < 1) iterations = 1;

    // 反復処理
    for (int i = 0; i < iterations; i++) {
        // ぼかし処理
        for (int y = 1; y <= h; y++) {
            for (int x = 1; x <= w; x++) {
                double sum = 0.0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        sum += in_padded[(y + dy) * w_pad + (x + dx)];
                    }
                }
                out_padded[y * w_pad + x] = sum / 9.0;
            }
        }

        // パディング画像を更新
        memcpy(in_padded, out_padded, h_pad * w_pad * sizeof(double));
    }

    // 出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = out_padded[(y + 1) * w_pad + (x + 1)];
        }
    }

    // メモリを解放
    free(in_padded);
    free(out_padded);
}
