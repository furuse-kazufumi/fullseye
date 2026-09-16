#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 8近傍のインデックス
    int offsets[8] = {-w - 1, -w, -w + 1, -1, 1, w - 1, w, w + 1};

    // 各画素について境界を検出
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int idx = y * w + x;
            double center = in[idx];
            int boundary = 0;

            // 8近傍の各画素について、中心画素と異なるラベルであるかを確認
            for (int i = 0; i < 8; i++) {
                int neighbor_idx = idx + offsets[i];
                if (in[neighbor_idx] != center) {
                    boundary = 1;
                    break;
                }
            }

            // 境界画素の場合、出力画像に 1 を設定
            if (boundary) {
                out[idx] = 1.0;
            }
        }
    }
}
