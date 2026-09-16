#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の各画素を 0.0 か 1.0 に丸める
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = (in[y * w + x] >= 0.5) ? 1.0 : 0.0;
        }
    }

    // 4-連結性に基づいて穴を埋める
    // 穴の判定は内部の背景画素 (0.0) で、端の背景画素は埋めない
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            if (out[y * w + x] == 0.0) {
                // 4-連結性に基づいて周囲の画素を確認
                if (out[(y - 1) * w + x] == 1.0 ||
                    out[(y + 1) * w + x] == 1.0 ||
                    out[y * w + x - 1] == 1.0 ||
                    out[y * w + x + 1] == 1.0) {
                    out[y * w + x] = 1.0; // 穴を埋める
                }
            }
        }
    }
}
