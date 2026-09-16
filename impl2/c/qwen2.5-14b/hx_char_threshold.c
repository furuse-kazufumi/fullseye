#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a は [0,1] の範囲で、係数 k を計算する。
    double k = 0.2 + 1.8 * a;

    // 画像全体の平均と標準偏差を計算
    double sum = 0.0;
    double sum_sq = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            sum += val;
            sum_sq += val * val;
        }
    }
    double mean = sum / (h * w);
    double std = sqrt((sum_sq / (h * w)) - (mean * mean));

    // しきい値を計算
    double thr = mean - k * std;

    // 画像の各画素に対して、しきい値以下の場合 1.0、それ以外の場合 0.0 を出力
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            out[y * w + x] = (val < thr) ? 1.0 : 0.0;
        }
    }
}
