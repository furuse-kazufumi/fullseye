#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 二値画像の処理を想定。入力画像は 0.0 または 1.0 のみ。
    // 出力画像も 0.0 または 1.0 のみを設定する。

    // 最小ラン長の計算
    int min_len = 1 + MAX(1, (int)round(8 * a));

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各行について処理
    for (int y = 0; y < h; y++) {
        int start = y * w;  // 行の開始位置
        int end = (y + 1) * w;  // 行の終了位置

        // 前の画素が 1 かどうかを追跡
        int prev_pixel = 0;
        int run_length = 0;

        // 行内の各画素について処理
        for (int x = 0; x < w; x++) {
            int current_pixel = (int)in[start + x];

            // 画素が 1 で、前の画素が 0 だった場合、新しいランの開始
            if (current_pixel == 1 && prev_pixel == 0) {
                run_length = 1;
            }
            // 画素が 1 で、前の画素も 1 だった場合、ランの延長
            else if (current_pixel == 1 && prev_pixel == 1) {
                run_length++;
            }
            // 画素が 0 で、前の画素が 1 だった場合、ランの終了
            else if (current_pixel == 0 && prev_pixel == 1) {
                // ランが最小長を超えていれば、出力画像に設定
                if (run_length >= min_len) {
                    for (int i = 0; i < run_length; i++) {
                        out[start + x - i - 1] = 1;
                    }
                }
                run_length = 0;
            }

            prev_pixel = current_pixel;
        }

        // 最後のランの処理
        if (run_length >= min_len) {
            for (int i = 0; i < run_length; i++) {
                out[start + w - i - 1] = 1;
            }
        }
    }
}
