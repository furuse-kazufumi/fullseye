#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を背景(0)とみなす。
    // 3x3 マスクを用いて、各画素の 3x3 近傍に 3 つ以上の骨格画素を持つ画素を検出する。
    // 1.0 は領域に属する画素を表す。出力は 0.0 か 1.0 の二値。

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 3x3 マスクを用いて各画素の近傍をチェック
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int count = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (in[(y + dy) * w + (x + dx)] > 0.5) {
                        count++;
                    }
                }
            }
            // 3x3 近傍に 3 つ以上の骨格画素を持つ画素を出力に書き込む
            if (count >= 3) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
