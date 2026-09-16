#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ブロックサイズの計算
    int block_size = 2 * (int)(a * 6) + 3;
    // ブロックサイズが奇数であることを確認
    if (block_size % 2 == 0) {
        block_size++;
    }

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 局所中央値適応的二値化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 局所領域の中央値を計算
            double median_value = 0.0;
            int count = 0;
            for (int dy = -block_size / 2; dy <= block_size / 2; dy++) {
                for (int dx = -block_size / 2; dx <= block_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        median_value += in[ny * w + nx];
                        count++;
                    }
                }
            }
            median_value /= count;

            // 二値化
            if (in[y * w + x] > median_value) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
