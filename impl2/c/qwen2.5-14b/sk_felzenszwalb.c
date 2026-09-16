#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // ここでは、a パラメータを用いてスケールを調整し、境界を検出します。
    // b パラメータは使用しません。
    // スケールの計算
    double scale = 20 + 200 * a;
    
    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));
    
    // 画像の各画素に対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 画素のインデックス
            int idx = y * w + x;
            
            // 画素の値
            double pixel_value = in[idx];
            
            // 簡易的な境界検出
            // ここでは、画素の値がスケール値を超える場合、境界として扱います。
            if (pixel_value > scale) {
                out[idx] = 1.0;
            }
        }
    }
}
