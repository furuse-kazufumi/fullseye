#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径の計算
    int radius = (int)round(a * 4); // 半径は 0 から 4 まで
    if (radius < 0) radius = 0;
    if (radius > 4) radius = 4;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の境界外を無視
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }
}
