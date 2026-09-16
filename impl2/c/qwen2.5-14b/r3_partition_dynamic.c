#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の画素は背景(0)とみなす。
    // 密度の計算では、端の画素を含まない。

    // 最大密度を計算
    int max_density = 0;
    for (int y = 0; y < h; y++) {
        int density = 0;
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                density++;
            }
        }
        if (density > max_density) {
            max_density = density;
        }
    }

    // 密度が最大密度の割合 a 以下である列をゼロに潰す
    for (int y = 0; y < h; y++) {
        int density = 0;
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                density++;
            }
        }
        if (density <= a * max_density) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] = 0.0;
            }
        } else {
            for (int x = 0; x < w; x++) {
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
