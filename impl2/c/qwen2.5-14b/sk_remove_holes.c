#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // しきい値の計算
    int area_threshold = 8 + (int)(a * 60);
    // 入力画像のコピーを作成
    double* temp = (double*)malloc(h * w * sizeof(double));
    memcpy(temp, in, h * w * sizeof(double));

    // ホールの除去
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 4近傍のマスク
            int mask[4] = {temp[(y - 1) * w + x], temp[y * w + x - 1], temp[y * w + x + 1], temp[(y + 1) * w + x]};
            int hole_size = 0;

            // ホールのサイズを計算
            for (int i = 0; i < 4; i++) {
                if (mask[i] == 0) {
                    hole_size++;
                }
            }

            // ホールのサイズがしきい値未満の場合、穴を埋める
            if (hole_size > 0 && hole_size < area_threshold) {
                temp[y * w + x] = 1.0;
            }
        }
    }

    // 出力画像にコピー
    memcpy(out, temp, h * w * sizeof(double));

    // メモリ解放
    free(temp);
}
