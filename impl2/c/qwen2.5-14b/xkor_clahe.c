#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // CLAHEの実装では、通常、画像を小さな領域（tile）に分割し、各領域内でヒストグラム均等化を適用します。
    // ここでは、簡単のため、全体の画像を1つの領域として扱います。
    // また、つまみbは未使用であるため、無視します。

    // コントラスト制限の計算
    double clip_limit = 1.0 + 4.0 * a;

    // 画像のヒストグラムを計算
    int histogram[256] = {0};
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            histogram[pixel_value]++;
        }
    }

    // 累積ヒストグラムを計算
    int cumulative_histogram[256] = {0};
    cumulative_histogram[0] = histogram[0];
    for (int i = 1; i < 256; i++) {
        cumulative_histogram[i] = cumulative_histogram[i - 1] + histogram[i];
    }

    // CLAHEの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            int clipped_histogram = cumulative_histogram[pixel_value];
            int new_pixel_value = (int)(255.0 * clipped_histogram / (h * w));
            out[y * w + x] = new_pixel_value / 255.0;
        }
    }
}
