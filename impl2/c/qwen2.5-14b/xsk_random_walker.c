#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double dark_seed_threshold = 0.3 + 0.2 * a;
    const double bright_seed_threshold = 0.7 - 0.2 * a;
    const double beta = 10 + 200 * b;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 各画素のラベルを決定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int label = 0;
            double pixel_value = in[y * w + x];

            // シードの生成
            if (pixel_value < dark_seed_threshold) {
                label = 1;
            } else if (pixel_value > bright_seed_threshold) {
                label = 2;
            }

            // ラベルの決定
            if (label == 0) {
                // 周囲の画素のラベルを考慮
                int neighbors[4] = {0, 0, 0, 0};
                int neighbor_count = 0;

                // 上の画素
                if (y > 0) {
                    neighbors[neighbor_count++] = (int)out[(y - 1) * w + x];
                }
                // 下の画素
                if (y < h - 1) {
                    neighbors[neighbor_count++] = (int)out[(y + 1) * w + x];
                }
                // 左の画素
                if (x > 0) {
                    neighbors[neighbor_count++] = (int)out[y * w + x - 1];
                }
                // 右の画素
                if (x < w - 1) {
                    neighbors[neighbor_count++] = (int)out[y * w + x + 1];
                }

                // ラベルの決定
                int dark_neighbor_count = 0;
                int bright_neighbor_count = 0;
                for (int i = 0; i < neighbor_count; i++) {
                    if (neighbors[i] == 1) {
                        dark_neighbor_count++;
                    } else if (neighbors[i] == 2) {
                        bright_neighbor_count++;
                    }
                }

                // ラベルの決定
                if (dark_neighbor_count > bright_neighbor_count) {
                    label = 1;
                } else if (bright_neighbor_count > dark_neighbor_count) {
                    label = 2;
                } else {
                    // エッジをまたいだ伝播を抑制
                    if (dark_neighbor_count > 0 && bright_neighbor_count > 0) {
                        label = 0;
                    } else if (dark_neighbor_count > 0) {
                        label = 1;
                    } else if (bright_neighbor_count > 0) {
                        label = 2;
                    }
                }
            }

            // 出力画像への書き込み
            if (label == 1 || label == 2) {
                out[y * w + x] = (label == 1) ? 0.0 : 1.0;
            }
        }
    }
}
