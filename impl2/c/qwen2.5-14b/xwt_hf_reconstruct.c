#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ここでは、入力画像を小波変換 (Wavelet Transform) にかけるための仮の実装を想定しています。
    // 本実装では、小波変換の詳細な実装は省略し、代わりに高周波成分を強調するための単純なフィルタリングを適用します。
    // 低周波成分を除去し、高周波成分を強調するためのフィルタリングは、具体的には差分フィルタを適用することで実現します。
    // 画像の端の処理については、境界外のピクセルは端のピクセルの値を用いることにします。

    // 差分フィルタを適用するための一時的な配列を確保
    double* diff = (double*)malloc(h * w * sizeof(double));
    if (diff == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 差分フィルタを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            // 差分フィルタの適用 (境界外のピクセルは端のピクセルの値を用いる)
            if (y > 0) {
                value += in[(y - 1) * w + x] - in[y * w + x];
            }
            if (y < h - 1) {
                value += in[(y + 1) * w + x] - in[y * w + x];
            }
            if (x > 0) {
                value += in[y * w + x - 1] - in[y * w + x];
            }
            if (x < w - 1) {
                value += in[y * w + x + 1] - in[y * w + x];
            }
            diff[y * w + x] = fabs(value);
        }
    }

    // 差分フィルタの結果を出力配列にコピー
    memcpy(out, diff, h * w * sizeof(double));

    // 最大値で正規化
    double max_value = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }
    if (max_value > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_value;
        }
    }

    // メモリを解放
    free(diff);
}
