#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ヒストグラムの初期化
    int histogram[256] = {0};
    int total_pixels = h * w;
    double sum = 0.0;
    double sumB = 0.0;

    // ヒストグラムの計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            histogram[pixel_value]++;
            sum += pixel_value;
        }
    }

    // Otsu の二値化アルゴリズムの適用
    double max_variance = 0.0;
    int threshold = 0;
    for (int t = 0; t < 256; t++) {
        double wB = 0.0;
        double wF = 0.0;
        double mB = 0.0;
        double mF = 0.0;

        for (int i = 0; i <= t; i++) {
            wB += histogram[i];
            mB += (double)(i * histogram[i]);
        }
        wB /= total_pixels;
        mB /= wB;

        for (int i = t + 1; i < 256; i++) {
            wF += histogram[i];
            mF += (double)(i * histogram[i]);
        }
        wF /= total_pixels;
        mF /= wF;

        if (wB == 0 || wF == 0) {
            continue;
        }

        double variance = wB * wF * pow((mB - mF), 2);
        if (variance > max_variance) {
            max_variance = variance;
            threshold = t;
        }
    }

    // 二値化の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int pixel_value = (int)(in[y * w + x] * 255.0);
            out[y * w + x] = (pixel_value > threshold) ? 1.0 : 0.0;
        }
    }
}
