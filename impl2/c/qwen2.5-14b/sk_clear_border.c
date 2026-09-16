#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。

    // 入力画像のコピーを作成
    double* in_copy = (double*)malloc(h * w * sizeof(double));
    memcpy(in_copy, in, h * w * sizeof(double));

    // 画像の端の画素を複製する(最近傍)
    for (int y = 0; y < h; ++y) {
        in_copy[y * w] = in_copy[y * w + 1]; // 左端
        in_copy[y * w + w - 1] = in_copy[y * w + w - 2]; // 右端
    }
    for (int x = 0; x < w; ++x) {
        in_copy[x] = in_copy[w]; // 上端
        in_copy[(h - 1) * w + x] = in_copy[(h - 2) * w + x]; // 下端
    }

    // 画像端に接する成分の除去
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // 4-conn ネイバーのうち、1 つでも 0 があれば、その画素は 0 に設定
            if (in_copy[(y - 1) * w + x] == 0 || in_copy[(y + 1) * w + x] == 0 ||
                in_copy[y * w + x - 1] == 0 || in_copy[y * w + x + 1] == 0) {
                out[y * w + x] = 0;
            } else {
                out[y * w + x] = in_copy[y * w + x];
            }
        }
    }

    // 呼び出し側が確保したメモリを解放
    free(in_copy);
}
