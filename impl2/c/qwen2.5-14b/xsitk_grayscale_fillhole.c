#include <math.h>
#include <stdlib.h>
#include <string.h>

// 定義: 画像の周囲を拡張するためのパディング値
#define PAD_VALUE 0.0

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 出力画像のサイズ
    int out_h = h;
    int out_w = w;

    // パディングされた画像のサイズ
    int padded_h = h + 2;
    int padded_w = w + 2;

    // パディングされた画像の確保
    double* padded_img = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_img == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 入力画像をパディングされた画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_img[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // パディングの初期化
    for (int y = 0; y < padded_h; y++) {
        padded_img[y * padded_w] = PAD_VALUE;
        padded_img[y * padded_w + padded_w - 1] = PAD_VALUE;
    }
    for (int x = 0; x < padded_w; x++) {
        padded_img[x] = PAD_VALUE;
        padded_img[(padded_h - 1) * padded_w + x] = PAD_VALUE;
    }

    // モルフォロジー再構成による穴埋め処理
    for (int iter = 0; iter < 10; iter++) { // 10 回の反復で穴埋め処理を終了
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double max_value = PAD_VALUE;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        double neighbor_value = padded_img[(y + dy + 1) * padded_w + (x + dx + 1)];
                        if (neighbor_value > max_value) {
                            max_value = neighbor_value;
                        }
                    }
                }
                padded_img[(y + 1) * padded_w + (x + 1)] = max_value;
            }
        }
    }

    // パディングされた画像から出力画像をコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = padded_img[(y + 1) * padded_w + (x + 1)];
            // 出力を [0,1] の範囲にクリップ
            if (out[y * w + x] < 0.0) out[y * w + x] = 0.0;
            if (out[y * w + x] > 1.0) out[y * w + x] = 1.0;
        }
    }

    // パディングされた画像のメモリを解放
    free(padded_img);
}
