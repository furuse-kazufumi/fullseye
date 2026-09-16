#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は半径のスケーリングファクター。b は未使用。
    int radius = (int)(a * 4); // 半径は 0 から 4 まで。
    if (radius < 0) radius = 0;
    if (radius > 4) radius = 4;

    // 出力画像をクリア
    memset(out, 0, h * w * sizeof(double));

    // 円形構造要素のマスクを生成
    int mask_size = 2 * radius + 1;
    double* mask = (double*)malloc(mask_size * mask_size * sizeof(double));
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x * x + y * y <= radius * radius) {
                mask[(y + radius) * mask_size + (x + radius)] = 1.0;
            } else {
                mask[(y + radius) * mask_size + (x + radius)] = 0.0;
            }
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
            if (out[y * w + x] == 1.0) {
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
                if (count > 0) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            }
        }
    }

    // メモリを解放
    free(mask);
}
