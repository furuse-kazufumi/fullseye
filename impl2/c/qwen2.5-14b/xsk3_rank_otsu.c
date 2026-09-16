#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円盤半径の計算
    int radius = 2 + (int)(a * 8);
    int radius_squared = radius * radius;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 局所大津二値化の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 局所領域のピクセル値の取得
            double local_pixels[256] = {0};
            int pixel_count[256] = {0};
            int local_count = 0;

            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w && (dx * dx + dy * dy) <= radius_squared) {
                        int pixel_value = (int)(in[ny * w + nx] * 255);
                        local_pixels[pixel_value]++;
                        pixel_count[pixel_value]++;
                        local_count++;
                    }
                }
            }

            // 局所大津二値化の計算
            double max_variance = 0;
            int threshold = 0;
            for (int t = 0; t < 256; t++) {
                double w1 = 0, w2 = 0, m1 = 0, m2 = 0, var = 0;
                for (int i = 0; i <= t; i++) {
                    w1 += pixel_count[i];
                    m1 += i * pixel_count[i];
                }
                for (int i = t + 1; i < 256; i++) {
                    w2 += pixel_count[i];
                    m2 += i * pixel_count[i];
                }
                if (w1 > 0 && w2 > 0) {
                    m1 /= w1;
                    m2 /= w2;
                    var = w1 * w2 * pow(m1 - m2, 2);
                    if (var > max_variance) {
                        max_variance = var;
                        threshold = t;
                    }
                }
            }

            // 二値化の適用
            if (in[y * w + x] * 255 > threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
