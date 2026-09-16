#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は反復回数を 3〜6 に設定。b は無視。
    int iterations = (int)(a * 3) + 3; // 0.1 -> 3, 0.5 -> 5, 0.9 -> 6
    int border_value = 1; // 二値クロージングの境界値

    // 出力領域を入力と同じ形状で初期化
    memset(out, 0, h * w * sizeof(double));

    // 入力画像のコピーを作成
    double* temp = (double*)malloc(h * w * sizeof(double));
    memcpy(temp, in, h * w * sizeof(double));

    // 反復回数分クロージングを実行
    for (int i = 0; i < iterations; i++) {
        // Erosion (二値クロージングの前半)
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                if (temp[y * w + x] == border_value) {
                    if (temp[(y - 1) * w + x - 1] == border_value &&
                        temp[(y - 1) * w + x] == border_value &&
                        temp[(y - 1) * w + x + 1] == border_value &&
                        temp[y * w + x - 1] == border_value &&
                        temp[y * w + x + 1] == border_value &&
                        temp[(y + 1) * w + x - 1] == border_value &&
                        temp[(y + 1) * w + x] == border_value &&
                        temp[(y + 1) * w + x + 1] == border_value) {
                        out[y * w + x] = border_value;
                    }
                }
            }
        }

        // Dilation (二値クロージングの後半)
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                if (out[y * w + x] == border_value) {
                    temp[(y - 1) * w + x - 1] = border_value;
                    temp[(y - 1) * w + x] = border_value;
                    temp[(y - 1) * w + x + 1] = border_value;
                    temp[y * w + x - 1] = border_value;
                    temp[y * w + x + 1] = border_value;
                    temp[(y + 1) * w + x - 1] = border_value;
                    temp[(y + 1) * w + x] = border_value;
                    temp[(y + 1) * w + x + 1] = border_value;
                }
            }
        }

        // 出力領域を更新
        memcpy(out, temp, h * w * sizeof(double));
    }

    // メモリを解放
    free(temp);
}
