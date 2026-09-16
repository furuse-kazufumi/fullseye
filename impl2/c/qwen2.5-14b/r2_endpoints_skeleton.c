#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。端点抽出アルゴリズムは二値画像の骨格の端点を抽出する。
    // 画像の外側は背景(0)とみなす。

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 8近傍を定義
    int neighbors[8][2] = {{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}};

    // 各画素について処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            // 8近傍の画素をチェック
            for (int i = 0; i < 8; i++) {
                int ny = y + neighbors[i][0];
                int nx = x + neighbors[i][1];
                // 画像の外側は背景(0)とみなす
                if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                    count += (int)in[ny * w + nx];
                }
            }
            // 8近傍にちょうど1個の骨格画素を持つ点を端点として抽出
            if (count == 1) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
