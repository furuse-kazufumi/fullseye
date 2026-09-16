#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円盤の半径を計算
    int radius = 1 + (int)(a * 3);
    int disk_size = 2 * radius + 1;

    // 円盤のマスクを作成
    int* disk_mask = (int*)malloc(disk_size * disk_size * sizeof(int));
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x * x + y * y <= radius * radius) {
                disk_mask[(y + radius) * disk_size + (x + radius)] = 1;
            } else {
                disk_mask[(y + radius) * disk_size + (x + radius)] = 0;
            }
        }
    }

    // 画像の各画素に対してエントロピーを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 画素の周辺のグレー値分布を取得
            int* histogram = (int*)calloc(256, sizeof(int));
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        int value = (int)(in[ny * w + nx] * 255);
                        histogram[value]++;
                    }
                }
            }

            // エントロピーを計算
            double entropy = 0.0;
            for (int i = 0; i < 256; i++) {
                if (histogram[i] > 0) {
                    double p = (double)histogram[i] / (disk_size * disk_size);
                    entropy -= p * log2(p);
                }
            }

            // エントロピーを出力画像に格納
            out[y * w + x] = entropy / log2(256); // 正規化

            // ヒストグラムを解放
            free(histogram);
        }
    }

    // 円盤のマスクを解放
    free(disk_mask);
}
