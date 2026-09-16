#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は反復回数を 1〜4 に振る。
    int iterations = (int)round(a * 3) + 1; // 0.1 -> 1, 0.5 -> 2, 0.9 -> 4

    // 出力領域を確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 初期化
    memcpy(temp, in, h * w * sizeof(double));

    // 膨張処理
    for (int i = 0; i < iterations; i++) {
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                // 8近傍の最大値を求める
                double max_val = 0.0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (temp[(y + dy) * w + (x + dx)] > max_val) {
                            max_val = temp[(y + dy) * w + (x + dx)];
                        }
                    }
                }
                // 出力に最大値を設定
                out[y * w + x] = max_val;
            }
        }
        // 次の反復のための準備
        memcpy(temp, out, h * w * sizeof(double));
    }

    // メモリ解放
    free(temp);
}
