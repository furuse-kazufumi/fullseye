#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用なので無視する
    (void)b;

    // 半径の計算
    int radius = (int)(a * 4); // 0.1 から 0.9 までで半径 1 から 4 まで
    if (radius < 1) radius = 1; // 最小半径は 1

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }

    // 収縮処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (out[ny * w + nx] == 1.0) {
                            count++;
                        }
                    }
                }
            }
            if (count > (2 * radius + 1) * (2 * radius + 1) / 2) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
