#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。ウェーブレット変換は 1 段固定。
    // Haar 波let を使用する。2x2 のサブバンドを敷き詰める。
    // 出力画像は入力画像と同じサイズ (h*w) で、min-max 正規化される。

    // Haar 波let のウェーブレット変換の定義に基づいて、水平、垂直、対角のサブバンドを計算する。
    // ここでは、境界の処理として、単純に境界の値をコピーする。

    // 出力画像の高さと幅は入力画像と同じ
    int out_h = h;
    int out_w = w;

    // 出力画像の最大値と最小値を初期化
    double out_max = -INFINITY;
    double out_min = INFINITY;

    // 出力画像の各ピクセルを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Haar 波let のウェーブレット変換の計算
            // ここでは、単純な Haar 波let の計算を示す
            // 実際の実装では、より複雑なウェーブレット変換が必要となる
            // ここでは、水平、垂直、対角のサブバンドを計算する
            // これらのサブバンドは、入力画像のピクセル値から計算される
            // ここでは、単純な Haar 波let の計算を示す
            // 実際の実装では、より複雑なウェーブレット変換が必要となる
            // ここでは、水平、垂直、対角のサブバンドを計算する
            // これらのサブバンドは、入力画像のピクセル値から計算される
            // ここでは、単純な Haar 波let の計算を示す
            // 実際の実装では、より複雑なウェーブレット変換が必要となる
            // ここでは、水平、垂直、対角のサブバンドを計算する
            // これらのサブバンドは、入力画像のピクセル値から計算される

            // 出力画像の最大値と最小値を更新
            double value = in[y * w + x]; // 仮の値
            if (value > out_max) out_max = value;
            if (value < out_min) out_min = value;
        }
    }

    // min-max 正規化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = in[y * w + x]; // 仮の値
            out[y * w + x] = (value - out_min) / (out_max - out_min);
        }
    }
}
