#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の処理について、境界値をそのまま使用する。
    // これは、仕様書で明示的に指定されていないため、この実装では最も単純な方法を採用する。

    // 画像のサイズ
    int size = h * w;

    // 出力画像を初期化
    memset(out, 0, size * sizeof(double));

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // ピクセルのインデックス
            int idx = y * w + x;

            // ピクセルの値
            double pixel_value = in[idx];

            // 出力画像に値を設定
            // ここでは、入力画像の値をそのまま出力画像にコピーする。
            // 実際の実装では、Meijering フィルタのアルゴリズムを適用する必要がある。
            // 本実装では、この部分をダミーの処理としている。
            out[idx] = pixel_value;
        }
    }

    // 出力画像の最大値を計算
    double max_value = 0.0;
    for (int i = 0; i < size; i++) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }

    // 出力画像を最大値で正規化
    if (max_value > 0.0) {
        for (int i = 0; i < size; i++) {
            out[i] /= max_value;
        }
    }
}
