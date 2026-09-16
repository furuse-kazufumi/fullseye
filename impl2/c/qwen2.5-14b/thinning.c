#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の画素は背景（0）とみなす。
    // これは仕様書で明示的に指定されていないため、この実装ではこの選択を採用する。

    // 出力画像を入力画像と同じ値で初期化
    memcpy(out, in, h * w * sizeof(double));

    // スケletonization の各ステップを実装
    int step = 0;
    while (1) {
        int changed = 0;
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                if (out[y * w + x] == 1.0) {
                    // Zhang-Suen の条件をチェック
                    int p2 = out[(y - 1) * w + (x - 1)];
                    int p3 = out[(y - 1) * w + x];
                    int p4 = out[(y - 1) * w + (x + 1)];
                    int p5 = out[y * w + (x + 1)];
                    int p6 = out[(y + 1) * w + (x + 1)];
                    int p7 = out[(y + 1) * w + x];
                    int p8 = out[(y + 1) * w + (x - 1)];
                    int p9 = out[y * w + (x - 1)];

                    int A = p2 * p3 * p4 + p4 * p5 * p6 + p6 * p7 * p8 + p8 * p9 * p2;
                    int B = p2 * p3 + p3 * p4 + p4 * p5 + p5 * p6 + p6 * p7 + p7 * p8 + p8 * p9 + p9 * p2;
                    int m = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9;
                    int n = p3 + p4 + p5 + p6 + p7 + p8 + p9 + p2;

                    if (A == 1 && B >= 2 && B <= 6 && m == 1) {
                        out[y * w + x] = 0.0;
                        changed = 1;
                    }
                    if (A == 1 && B >= 2 && B <= 6 && n == 1) {
                        out[y * w + x] = 0.0;
                        changed = 1;
                    }
                }
            }
        }
        if (!changed) {
            break;
        }
        step++;
    }
}
