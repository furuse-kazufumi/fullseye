#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 平滑化強度 lambda の計算
    double lambda = 1.0 + 10.0 * a;

    // 辺の境界をミラー反射で処理するための補間画像の作成
    int h_padded = h + 2;
    int w_padded = w + 2;
    double* in_padded = (double*)malloc(h_padded * w_padded * sizeof(double));

    // 元の画像をミラー反射で補間画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            in_padded[(y + 1) * w_padded + (x + 1)] = in[y * w + x];
        }
    }

    // 左右のミラー反射
    for (int y = 0; y < h_padded; y++) {
        in_padded[y * w_padded] = in_padded[y * w_padded + 1];
        in_padded[(y + 1) * w_padded - 1] = in_padded[(y + 1) * w_padded - 2];
    }

    // 上下のミラー反射
    for (int x = 0; x < w_padded; x++) {
        in_padded[x] = in_padded[w_padded + x];
        in_padded[(h_padded - 1) * w_padded + x] = in_padded[(h_padded - 2) * w_padded + x];
    }

    // 3次スプラインフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    sum += in_padded[(y + dy + 1) * w_padded + (x + dx + 1)] * exp(-lambda * (dx * dx + dy * dy));
                }
            }
            out[y * w + x] = fmax(0.0, fmin(1.0, sum)); // [0,1] にクリップ
        }
    }

    free(in_padded);
}
