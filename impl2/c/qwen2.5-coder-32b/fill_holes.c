#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // コピー元画像を出力画像にコピー
    memcpy(out, in, h * w * sizeof(double));

    // 画像の各ピクセルを走査
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 画像の端にあるピクセルは処理しない
            if (y == 0 || y == h - 1 || x == 0 || x == w - 1) {
                continue;
            }

            // 現在のピクセルが背景(0.0)であるかチェック
            if (out[y * w + x] == 0.0) {
                // 周囲の8近傍がすべて前景(1.0)であるかチェック
                if (out[(y - 1) * w + (x - 1)] == 1.0 &&
                    out[(y - 1) * w + x] == 1.0 &&
                    out[(y - 1) * w + (x + 1)] == 1.0 &&
                    out[y * w + (x - 1)] == 1.0 &&
                    out[y * w + (x + 1)] == 1.0 &&
                    out[(y + 1) * w + (x - 1)] == 1.0 &&
                    out[(y + 1) * w + x] == 1.0 &&
                    out[(y + 1) * w + (x + 1)] == 1.0) {
                    // 周囲がすべて前景であれば、現在のピクセルを前景に変更
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
