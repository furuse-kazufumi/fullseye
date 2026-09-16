#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の画素は背景(0)とみなす。
    // これは仕様書の「端の扱い」セクションで明示されている。

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 8近傍のインデックス
    int neighbors[8][2] = {{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}};

    // 各画素について処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) { // 画素が骨格画素である場合
                int nb = 0; // 8近傍の骨格画素数
                for (int i = 0; i < 8; i++) {
                    int ny = y + neighbors[i][0];
                    int nx = x + neighbors[i][1];
                    // 画像の外側は背景(0)とみなす
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && in[ny * w + nx] > 0.5) {
                        nb++;
                    }
                }
                // nb >= 3 の画素(分岐点)を取り除く
                if (nb < 3) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
