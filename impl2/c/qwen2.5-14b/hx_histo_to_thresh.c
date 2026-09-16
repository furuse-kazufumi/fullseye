#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 64-bin ヒストグラムを作成
    int bins = 64;
    double hist[bins];
    memset(hist, 0, sizeof(hist));

    // 入力画像からヒストグラムを作成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int bin = (int)(in[y * w + x] * bins);
            if (bin >= bins) bin = bins - 1; // 範囲外の値を処理
            hist[bin]++;
        }
    }

    // ヒストグラムをガウス平滑化
    double sigma = 1.5;
    double gaussian[bins];
    for (int i = 0; i < bins; i++) {
        gaussian[i] = exp(-0.5 * (i - bins / 2) * (i - bins / 2) / (sigma * sigma));
    }
    double smoothed_hist[bins];
    for (int i = 0; i < bins; i++) {
        double sum = 0.0;
        for (int j = 0; j < bins; j++) {
            sum += hist[j] * gaussian[(i - j + bins) % bins];
        }
        smoothed_hist[i] = sum;
    }

    // 最も高い bin を探す
    int p1 = 0;
    for (int i = 1; i < bins; i++) {
        if (smoothed_hist[i] > smoothed_hist[p1]) p1 = i;
    }

    // p1 から 5 bin 以上離れた中で次に高い bin を探す
    int p2 = -1;
    for (int i = 0; i < bins; i++) {
        if (i < p1 - 5 || i > p1 + 5) {
            if (p2 == -1 || smoothed_hist[i] > smoothed_hist[p2]) p2 = i;
        }
    }

    // p2 が見つからない場合は thr = 0.5
    double thr = p2 == -1 ? 0.5 : (double)p1 / bins;

    // しきい値で二値化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x] > thr ? 1.0 : 0.0;
        }
    }
}
