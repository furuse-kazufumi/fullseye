#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が反復回数を 3〜6 に振る。b は未使用。
    int iterations = (int)(3.0 + 3.0 * a);
    int x, y, dx, dy;
    int nh = h + 2;
    int nw = w + 2;
    double* temp = (double*)malloc(nh * nw * sizeof(double));
    double* current = out;
    double* next = temp;

    // 境界を 0 で埋める
    memset(temp, 0, nh * nw * sizeof(double));

    // 元の画像を temp の中央にコピー
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            temp[(y + 1) * nw + (x + 1)] = in[y * w + x];
        }
    }

    // クロージングを iterations 回行う
    for (int iter = 0; iter < iterations; iter++) {
        for (y = 1; y < nh - 1; y++) {
            for (x = 1; x < nw - 1; x++) {
                if (current[y * nw + x] == 1.0) {
                    next[y * nw + x] = 1.0;
                    continue;
                }
                for (dy = -1; dy <= 1; dy++) {
                    for (dx = -1; dx <= 1; dx++) {
                        if (current[(y + dy) * nw + (x + dx)] == 1.0) {
                            next[y * nw + x] = 1.0;
                            goto next_pixel;
                        }
                    }
                }
                next[y * nw + x] = 0.0;
            next_pixel:;
            }
        }
        // current と next を交換
        double* tmp = current;
        current = next;
        next = tmp;
    }

    // 結果を out にコピー
    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            out[y * w + x] = current[(y + 1) * nw + (x + 1)];
        }
    }

    // 一時領域を解放
    free(temp);
}
