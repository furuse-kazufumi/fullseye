#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は反復回数を 1〜4 に振る。b は未使用。
    int iterations = (int)round(a * 3 + 1); // 0.1 -> 1, 0.5 -> 2, 0.9 -> 4
    int kernel_size = 2; // 4近傍相当の構造要素。十字形の半径。

    // 出力画像を入力画像と同じ形状で初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 侵食処理
    for (int i = 0; i < iterations; i++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // 画素が領域に属するかチェック
                if (out[y * w + x] == 1.0) {
                    // 構造要素の範囲内にある画素全てが背景(0)であれば、現在の画素も背景(0)に変更
                    int all_background = 1;
                    for (int ky = -kernel_size; ky <= kernel_size; ky++) {
                        for (int kx = -kernel_size; kx <= kernel_size; kx++) {
                            int ny = y + ky;
                            int nx = x + kx;
                            // 画像の外側は背景(0)とみなす
                            if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                                continue;
                            }
                            if (out[ny * w + nx] != 0.0) {
                                all_background = 0;
                                break;
                            }
                        }
                        if (!all_background) break;
                    }
                    if (all_background) {
                        out[y * w + x] = 0.0;
                    }
                }
            }
        }
    }
}
