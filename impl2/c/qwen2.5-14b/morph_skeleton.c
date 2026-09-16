#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の外側は背景(0)とみなす。
    // 画像の端を背景(0)で埋める。
    // 画像の端の処理は、入力画像の端を背景(0)とみなすことで実装する。

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各画素に対して処理を行う
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 8近傍の画素を取得
            int neighbors[8] = {
                in[(y - 1) * w + (x - 1)], in[(y - 1) * w + x], in[(y - 1) * w + (x + 1)],
                in[y * w + (x - 1)], in[y * w + (x + 1)],
                in[(y + 1) * w + (x - 1)], in[(y + 1) * w + x], in[(y + 1) * w + (x + 1)]
            };

            // 画素が領域内(1)の場合
            if (in[y * w + x] == 1) {
                // 8近傍の画素の数をカウント
                int count = 0;
                for (int i = 0; i < 8; i++) {
                    if (neighbors[i] == 1) {
                        count++;
                    }
                }

                // 画素が端点の場合
                if (count == 1 || count == 2) {
                    out[y * w + x] = 1;
                }
                // 画素が枝の場合
                else if (count >= 3 && count <= 6) {
                    // 画素の8近傍の画素の数をカウント
                    int neighbor_count = 0;
                    for (int i = 0; i < 8; i++) {
                        if (neighbors[i] == 1) {
                            neighbor_count++;
                        }
                    }

                    // 画素の8近傍の画素の数が2の場合
                    if (neighbor_count == 2) {
                        out[y * w + x] = 1;
                    }
                }
            }
        }
    }
}
