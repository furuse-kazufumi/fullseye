#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 膨張半径の計算
    int it = 1 + (int)(a * 4); // it は 1 から 5 の範囲
    int radius = it; // 膨張半径

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 4近傍の十字構造要素を用いて領域を膨張させる
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                // 画素が領域に属する場合、その画素とその画素の4近傍をチェック
                for (int dy = -radius; dy <= radius; dy++) {
                    for (int dx = -radius; dx <= radius; dx++) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の範囲内に収まるかチェック
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0; // 膨張処理
                        }
                    }
                }
            }
        }
    }
}
