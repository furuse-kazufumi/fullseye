#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が構造要素の一辺を 3, 5, 7, 9 に振る。b は未使用。
    int k = (int)(a * 4) * 2 + 3; // a が [0,1] の範囲で 3, 5, 7, 9 のいずれかにマッピングされる。
    int k2 = k / 2; // 構造要素の半径

    // 一時的な画像バッファを確保
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        return; // メモリ確保に失敗した場合
    }

    // クロージング操作 (dilation followed by erosion)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_val = -INFINITY;
            for (int ky = -k2; ky <= k2; ky++) {
                for (int kx = -k2; kx <= k2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        max_val = fmax(max_val, in[ny * w + nx]);
                    }
                }
            }
            temp[y * w + x] = max_val;
        }
    }

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = INFINITY;
            for (int ky = -k2; ky <= k2; ky++) {
                for (int kx = -k2; kx <= k2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, temp[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }

    // ブラックトップハット操作 (クロージング - 原画像)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = fmax(0.0, out[y * w + x] - in[y * w + x]);
        }
    }

    // 一時的な画像バッファを解放
    free(temp);
}
