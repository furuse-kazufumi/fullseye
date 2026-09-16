#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 結構要素の半径を計算
    int r = 1 + (int)(a * 4);
    // 結構要素のサイズは 2r+1
    int kernel_size = 2 * r + 1;

    // 出力画像をクリア
    memset(out, 0, h * w * sizeof(double));

    // オープニング処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 収縮処理
            double eroded = 1.0;
            for (int ky = -r; ky <= r; ky++) {
                for (int kx = -r; kx <= r; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        eroded = eroded && (in[ny * w + nx] > 0.5);
                    } else {
                        eroded = 0.0;
                    }
                }
            }

            // 膨張処理
            double dilated = 0.0;
            if (eroded > 0.5) {
                for (int ky = -r; ky <= r; ky++) {
                    for (int kx = -r; kx <= r; kx++) {
                        int ny = y + ky;
                        int nx = x + kx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            dilated = dilated || (in[ny * w + nx] > 0.5);
                        }
                    }
                }
            }

            // 出力画像に書き込み
            out[y * w + x] = dilated;
        }
    }
}
