#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 初期化
    int total_pixels = h * w;
    double background_sum = 0.0;
    int background_count = 0;
    double* region_sums = (double*)malloc(total_pixels * sizeof(double));
    int* region_counts = (int*)malloc(total_pixels * sizeof(int));
    memset(region_sums, 0, total_pixels * sizeof(double));
    memset(region_counts, 0, total_pixels * sizeof(int));

    // フロアとスカイを分ける
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            double pixel_value = in[index];
            if (pixel_value > a) {
                region_sums[index] = pixel_value;
                region_counts[index] = 1;
            } else {
                background_sum += pixel_value;
                background_count++;
            }
        }
    }

    // 連結成分の平均を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (region_counts[index] > 0) {
                out[index] = region_sums[index] / region_counts[index];
            } else {
                if (background_count > 0) {
                    out[index] = background_sum / background_count;
                } else {
                    out[index] = 0.0;
                }
            }
        }
    }

    // メモリ解放
    free(region_sums);
    free(region_counts);
}
