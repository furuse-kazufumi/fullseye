#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))

// 定数
#define SLIC_SIZE 50
#define SLIC_COMPACTNESS 10

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // スーパーピクセルの数を計算
    int n_segments = 10 + 80 * a;
    int segment_size = (h * w) / n_segments;

    // スーパーピクセルの中心点を初期化
    double (*centers)[3] = malloc(n_segments * sizeof(double[3]));
    for (int i = 0; i < n_segments; i++) {
        centers[i][0] = (i * segment_size + segment_size / 2) % w;
        centers[i][1] = (i * segment_size + segment_size / 2) / w;
        centers[i][2] = in[(int)centers[i][1] * w + (int)centers[i][0]];
    }

    // SLIC アルゴリズムの実装
    for (int iter = 0; iter < SLIC_SIZE; iter++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double min_dist = INFINITY;
                int min_label = -1;
                for (int i = 0; i < n_segments; i++) {
                    double dist = pow(centers[i][0] - x, 2) + pow(centers[i][1] - y, 2) + SLIC_COMPACTNESS * pow(centers[i][2] - in[y * w + x], 2);
                    if (dist < min_dist) {
                        min_dist = dist;
                        min_label = i;
                    }
                }
                out[y * w + x] = (min_label == -1) ? 0 : 1;
            }
        }

        // 中心点の更新
        for (int i = 0; i < n_segments; i++) {
            double sum_x = 0, sum_y = 0, sum_c = 0, count = 0;
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    if (out[y * w + x] == 1) {
                        sum_x += x;
                        sum_y += y;
                        sum_c += in[y * w + x];
                        count++;
                    }
                }
            }
            if (count > 0) {
                centers[i][0] = sum_x / count;
                centers[i][1] = sum_y / count;
                centers[i][2] = sum_c / count;
            }
        }
    }

    free(centers);
}
