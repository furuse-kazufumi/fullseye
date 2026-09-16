#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素の半径を計算
    int radius = 1 + (int)(a * 3);
    int struct_size = 2 * radius + 1;

    // 出力画像を初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各ピクセルに対して処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double product = 1.0;
            int count = 0;

            // 構造要素の範囲内のピクセルに対して処理
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int sy = y + dy;
                    int sx = x + dx;

                    // 画像の範囲内に位置するピクセルのみ処理
                    if (sy >= 0 && sy < h && sx >= 0 && sx < w) {
                        product *= in[sy * w + sx];
                        count++;
                    }
                }
            }

            // 几何平均を計算
            if (count > 0) {
                out[y * w + x] = pow(product, 1.0 / count);
            } else {
                // 無視されるピクセルの場合は入力値をそのまま出力
                out[y * w + x] = in[y * w + x];
            }
        }
    }
}
