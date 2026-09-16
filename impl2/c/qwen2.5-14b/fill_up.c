#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。この関数では無視する。

    // 出力領域を初期化
    memset(out, 0, h * w * sizeof(double));

    // 8近傍を考慮するためのオフセット
    int offsets[8] = {-w - 1, -w, -w + 1, -1, 1, w - 1, w, w + 1};

    // フィルタリング処理
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int index = y * w + x;
            if (in[index] == 1.0) {
                out[index] = 1.0;
                continue;
            }

            // 8近傍の画素を確認
            int is_hole = 1;
            for (int i = 0; i < 8; i++) {
                int neighbor_index = index + offsets[i];
                if (in[neighbor_index] == 1.0) {
                    is_hole = 0;
                    break;
                }
            }

            // 穴を埋める
            if (is_hole) {
                out[index] = 1.0;
            }
        }
    }
}
