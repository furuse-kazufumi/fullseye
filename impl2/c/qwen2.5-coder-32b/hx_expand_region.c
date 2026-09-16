#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 膨張半径の計算
    int it = 1 + (int)(a * 4);
    if (it < 1) it = 1;
    if (it > 5) it = 5;

    // 出力を初期化
    memset(out, 0, sizeof(double) * h * w);

    // 4近傍の十字構造要素を使用した膨張処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                for (int dy = -it; dy <= it; dy++) {
                    for (int dx = -it; dx <= it; dx++) {
                        if (dy == 0 || dx == 0) { // 4近傍の十字構造要素
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                out[ny * w + nx] = 1.0;
                            }
                        }
                    }
                }
            }
        }
    }
}
