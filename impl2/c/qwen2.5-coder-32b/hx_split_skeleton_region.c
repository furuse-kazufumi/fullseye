#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を背景(0)とみなす
    int dx[] = {-1, -1, -1, 0, 1, 1, 1, 0};
    int dy[] = {-1, 0, 1, 1, 1, 0, -1, -1};

    // 出力を初期化
    memset(out, 0, sizeof(double) * h * w);

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                int nb = 0;
                for (int i = 0; i < 8; i++) {
                    int nx = x + dx[i];
                    int ny = y + dy[i];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && in[ny * w + nx] > 0.5) {
                        nb++;
                    }
                }
                if (nb < 3) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
