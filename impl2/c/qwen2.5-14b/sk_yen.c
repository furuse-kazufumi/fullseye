#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Yenの最大相関基準に基づく二値化処理
    // 入力画像のヒストグラムを計算し、エントロピーを最大化するしきい値を求める

    // ヒストグラムの計算
    int histogram[256] = {0};
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int value = (int)(in[y * w + x] * 255.0);
            histogram[value]++;
        }
    }

    // エントロピーを最大化するしきい値を求める
    double max_entropy = -1.0;
    int threshold = 0;
    for (int t = 0; t < 256; t++) {
        double entropy = 0.0;
        int total = h * w;
        int total1 = 0;
        int total2 = 0;
        for (int i = 0; i < t; i++) {
            total1 += histogram[i];
        }
        for (int i = t; i < 256; i++) {
            total2 += histogram[i];
        }
        if (total1 == 0 || total2 == 0) continue;

        double p1 = (double)total1 / total;
        double p2 = (double)total2 / total;
        entropy = -p1 * log(p1) - p2 * log(p2);
        if (entropy > max_entropy) {
            max_entropy = entropy;
            threshold = t;
        }
    }

    // しきい値を用いて二値化処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int value = (int)(in[y * w + x] * 255.0);
            out[y * w + x] = (value < threshold) ? 0.0 : 1.0;
        }
    }
}
