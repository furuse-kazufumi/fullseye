#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // b が 0.5 より大きい場合、8 連結を、それ以外の場合は 4 連結を採用する。
    int connectivity = (b > 0.5) ? 8 : 4;

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各画素について境界を判定
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 画素が領域に属するか否か
            int is_in_region = (int)in[y * w + x];

            // 画素が領域に属しない場合はスキップ
            if (!is_in_region) continue;

            // 画素の周囲の画素をチェック
            int is_boundary = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    // 8 連結の場合はすべての隣接画素をチェック
                    // 4 連結の場合は水平・垂直方向の隣接画素のみをチェック
                    if (connectivity == 8 || (abs(dx) + abs(dy) == 1)) {
                        int nx = x + dx;
                        int ny = y + dy;

                        // 画像の境界外を避ける
                        if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue;

                        // 隣接画素が領域に属しない場合、境界画素と判定
                        if (!in[ny * w + nx]) {
                            is_boundary = 1;
                            break;
                        }
                    }
                }
                if (is_boundary) break;
            }

            // 界画素の場合、出力画像に 1 を設定
            if (is_boundary) out[y * w + x] = 1.0;
        }
    }
}
