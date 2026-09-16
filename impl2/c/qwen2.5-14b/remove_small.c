#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の画素数
    int total_pixels = h * w;
    // 除去する領域の最小面積 (画素数)
    int min_area = (0.01 + 0.15 * a) * total_pixels;
    // 連結成分ラベル付け
    int* labels = (int*)malloc(total_pixels * sizeof(int));
    int* counts = (int*)malloc(total_pixels * sizeof(int));
    int num_labels = 0;

    // ラベル付け用の変数
    int label = 1;
    int x, y;

    // ラベル付け
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                // 上の画素が同じラベルならそれを継承
                if (y > 0 && in[(y - 1) * w + x] > 0.5) {
                    labels[y * w + x] = labels[(y - 1) * w + x];
                } else if (x > 0 && in[y * w + x - 1] > 0.5) {
                    labels[y * w + x] = labels[y * w + x - 1];
                } else {
                    labels[y * w + x] = label++;
                }
            } else {
                labels[y * w + x] = 0;
            }
        }
    }

    // ラベルのカウント
    memset(counts, 0, total_pixels * sizeof(int));
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            if (labels[y * w + x] > 0) {
                counts[labels[y * w + x] - 1]++;
            }
        }
    }

    // ラベルのフィルタリング
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            if (labels[y * w + x] > 0 && counts[labels[y * w + x] - 1] >= min_area) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // メモリ解放
    free(labels);
    free(counts);
}
