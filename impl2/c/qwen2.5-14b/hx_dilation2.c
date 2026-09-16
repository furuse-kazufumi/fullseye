#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円板半径の計算
    int r = 1 + (int)(a * 4); // 半径は 1 から 5 画素
    // 列方向のずらし量の計算
    int sh = (int)((b - 0.5) * 6); // ずらし量は -3 から 3 画素

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // マスクの作成
    int mask_size = 2 * r + 1;
    int mask[mask_size * mask_size];
    for (int y = -r; y <= r; y++) {
        for (int x = -r; x <= r; x++) {
            if (x * x + y * y <= r * r) {
                mask[(y + r) * mask_size + (x + r)] = 1;
            } else {
                mask[(y + r) * mask_size + (x + r)] = 0;
            }
        }
    }

    // 膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                for (int dy = -r; dy <= r; dy++) {
                    for (int dx = -r; dx <= r; dx++) {
                        if (mask[(dy + r) * mask_size + (dx + r)] == 1) {
                            int ny = y + dy;
                            int nx = x + dx;
                            // 画像の端を処理するための境界条件
                            // ここでは、端からはみ出た部分は反対側に現れるようにする
                            ny = (ny + h) % h;
                            nx = (nx + w) % w;
                            out[ny * w + nx] = 1.0;
                        }
                    }
                }
            }
        }
    }

    // 列方向のずらし
    double temp[h * w];
    memcpy(temp, out, h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int nx = (x + sh + w) % w;
            out[y * w + x] = temp[y * w + nx];
        }
    }
}
