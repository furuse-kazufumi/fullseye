#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、正方形のサイズを決定する。b は無視する。
    // 正方形のサイズは {3,5,7,9} のいずれか。a が 0.1, 0.5, 0.9 のとき、
    // 正方形のサイズはそれぞれ 3, 5, 7 となる。a が 0.1 から 0.9 までの間で
    // 線形補間されるとき、正方形のサイズは 3 から 7 の間で線形補間される。
    int kernel_size = (int)(3 + (7 - 3) * a); // a が 0.1 から 0.9 の間で線形補間

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 正方形構造要素の半径
    int radius = kernel_size / 2;

    // 入力画像の各画素に対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 正方形構造要素の中心が現在の画素のとき、その周囲の画素をチェック
            if (in[y * w + x] == 1.0) {
                int count = 0;
                for (int ky = -radius; ky <= radius; ky++) {
                    for (int kx = -radius; kx <= radius; kx++) {
                        int ny = y + ky;
                        int nx = x + kx;
                        // 画像の境界外を避ける
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (in[ny * w + nx] == 1.0) {
                                count++;
                            }
                        }
                    }
                }
                // 周囲の画素のうち、構造要素のサイズ分の画素が 1 である場合、
                // 出力画像の現在の画素を 1 に設定
                if (count == (kernel_size * kernel_size)) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
