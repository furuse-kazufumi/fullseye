#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、つまみ a, b は無視される。
    // 画像の端の処理については、境界外のピクセルは端のピクセルの値を用いる。

    // GFTT (Good Features To Track) は Shi-Tomasi のコーナー応答を計算する。
    // ここでは、単純化のため、各ピクセルのラプラシアンを計算し、その絶対値を取る。
    // その後、出力を最大値で正規化する。

    // ラプラシアンを計算するための一時的な配列
    double laplacian[h * w];

    // ラプラシアンの計算
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int idx = y * w + x;
            laplacian[idx] = in[(y - 1) * w + (x - 1)] +
                             in[(y - 1) * w + x] +
                             in[(y - 1) * w + (x + 1)] +
                             in[y * w + (x - 1)] +
                             in[y * w + x] * -4 +
                             in[y * w + (x + 1)] +
                             in[(y + 1) * w + (x - 1)] +
                             in[(y + 1) * w + x] +
                             in[(y + 1) * w + (x + 1)];
        }
    }

    // 絶対値を取る
    for (int i = 0; i < h * w; i++) {
        laplacian[i] = fabs(laplacian[i]);
    }

    // 最大値を求める
    double max_value = 0;
    for (int i = 0; i < h * w; i++) {
        if (laplacian[i] > max_value) {
            max_value = laplacian[i];
        }
    }

    // 正規化
    for (int i = 0; i < h * w; i++) {
        out[i] = laplacian[i] / max_value;
    }
}
