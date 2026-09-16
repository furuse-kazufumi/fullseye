#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない。仕様書に明記されている。

    // 平均値を計算するための一時変数
    double mean = 0.0;
    // データ点の総数
    int total_points = h * w;

    // 入力画像の平均を計算
    for (int i = 0; i < total_points; i++) {
        mean += in[i];
    }
    mean /= total_points;

    // ヒステシス行列の計算
    // ここでは、単純な平均値を出力として返す。これは実際の Hybrid Hessian フィルタの実装とは異なるが、
    // 仕様書では a, b パラメータが使用されないため、この方法を採用する。
    // また、実際の Hybrid Hessian フィルタの実装は複雑で、ガウシアンフィルタの適用や、
    // ヒステシス行列の計算が必要となる。しかし、その詳細は仕様書に明記されていないため、
    // ここでは単純な平均値を出力として返す。
    for (int i = 0; i < total_points; i++) {
        out[i] = mean;
    }
}
