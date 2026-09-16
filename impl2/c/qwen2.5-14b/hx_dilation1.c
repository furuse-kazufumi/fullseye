#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 半径 r の計算
    int r = 1 + (int)(a * 4);
    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 膨張処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > 0.5) {
                for (int dy = -r; dy <= r; ++dy) {
                    for (int dx = -r; dx <= r; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の範囲外は無視
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }
}
