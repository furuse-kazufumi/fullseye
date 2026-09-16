#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の画素を複製する(最近傍)と指定されているため、境界の計算時にこの方法を採用する。
    // ラプラシアンフィルタは3x3のカーネルを使用する。
    // ラプラシアンフィルタのカーネルは以下の通り:
    // 0 -1  0
    //-1  4 -1
    // 0 -1  0
    // 画像の各画素に対してラプラシアンフィルタを適用し、結果をmin-max正規化する。

    // 出力画像の最大値と最小値を初期化
    double max_val = -INFINITY;
    double min_val = INFINITY;

    // ラプラシアンフィルタを適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int idx = y * w + x;
            double laplacian = in[idx - w - 1] + in[idx - w + 1] + in[idx - 1] + in[idx + 1] + in[idx + w - 1] + in[idx + w + 1] - 6 * in[idx];
            out[idx] = laplacian;
            // 最大値と最小値を更新
            if (laplacian > max_val) max_val = laplacian;
            if (laplacian < min_val) min_val = laplacian;
        }
    }

    // 端の画素を複製
    for (int y = 0; y < h; y++) {
        out[y * w] = out[y * w + 1];
        out[(y + 1) * w - 1] = out[(y + 1) * w - 2];
    }
    for (int x = 0; x < w; x++) {
        out[x] = out[w + x];
        out[(h - 1) * w + x] = out[(h - 2) * w + x];
    }

    // min-max 正規化
    for (int i = 0; i < h * w; i++) {
        out[i] = (out[i] - min_val) / (max_val - min_val);
    }
}
