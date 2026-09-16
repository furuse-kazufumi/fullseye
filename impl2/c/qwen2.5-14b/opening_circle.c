#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円形構造要素の半径を計算
    int radius = (int)(a * 4); // 半径は 0 から 4 までの整数値
    if (radius < 0) radius = 0;
    if (radius > 4) radius = 4;

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 円形構造要素のマスクを生成
    int mask_size = 2 * radius + 1;
    int* mask = (int*)malloc(mask_size * mask_size * sizeof(int));
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x * x + y * y <= radius * radius) {
                mask[(y + radius) * mask_size + (x + radius)] = 1;
            } else {
                mask[(y + radius) * mask_size + (x + radius)] = 0;
            }
        }
    }

    // 收縮処理
    double* eroded = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && mask[(dy + radius) * mask_size + (dx + radius)] && in[ny * w + nx] == 1) {
                        count++;
                    }
                }
            }
            eroded[y * w + x] = (count == (radius + 1) * (radius + 1)) ? 1 : 0;
        }
    }

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && mask[(dy + radius) * mask_size + (dx + radius)] && eroded[ny * w + nx] == 1) {
                        count++;
                    }
                }
            }
            out[y * w + x] = (count > 0) ? 1 : 0;
        }
    }

    // メモリを解放
    free(mask);
    free(eroded);
}
