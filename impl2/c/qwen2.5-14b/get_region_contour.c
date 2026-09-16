#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。無視する。
    (void)a;
    (void)b;

    // 入力画像のコピーを作成。領域の収縮版を計算するために必要。
    double* in_copy = (double*)malloc(h * w * sizeof(double));
    if (in_copy == NULL) {
        // メモリ確保失敗時の処理。ここでは単に終了する。
        exit(EXIT_FAILURE);
    }
    memcpy(in_copy, in, h * w * sizeof(double));

    // 収縮版を計算
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 8近傍の画素の合計を計算
            int sum = (int)(in[(y - 1) * w + (x - 1)] + in[(y - 1) * w + x] + in[(y - 1) * w + (x + 1)] +
                            in[y * w + (x - 1)] + in[y * w + (x + 1)] +
                            in[(y + 1) * w + (x - 1)] + in[(y + 1) * w + x] + in[(y + 1) * w + (x + 1)]);
            // 8近傍のうち4つ以上が1の場合は1を、それ以外は0を設定
            in_copy[y * w + x] = (sum >= 4) ? 1.0 : 0.0;
        }
    }

    // 輪郭を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像の画素が1で、収縮版の画素が0の場合は輪郭画素として1を設定
            out[y * w + x] = (in[y * w + x] == 1.0 && in_copy[y * w + x] == 0.0) ? 1.0 : 0.0;
        }
    }

    // メモリを解放
    free(in_copy);
}
