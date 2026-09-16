#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Kirsch コンパスフィルタのカーネル
    double kernels[8][3][3] = {
        {{5, -3, -3}, {5, 0, -3}, {5, -3, -3}},
        {{5, 5, -3}, {5, 0, -3}, {-3, -3, -3}},
        {{-3, 5, 5}, {-3, 0, 5}, {-3, -3, -3}},
        {{-3, -3, 5}, {-3, 0, 5}, {5, -3, 5}},
        {{-3, -3, -3}, {5, 0, 5}, {5, 5, -3}},
        {{-3, -3, -3}, {-3, 0, 5}, {5, 5, 5}},
        {{5, -3, -3}, {-3, 0, 5}, {5, -3, -3}},
        {{5, 5, -3}, {-3, 0, -3}, {-3, -3, 5}}
    };

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 端の扱い: 端画素を重複させて折り返す
    // 画像の端を処理するための補間関数
    double interpolate(double x, double y) {
        if (x < 0) x = -x;
        if (y < 0) y = -y;
        if (x >= w) x = 2 * w - x - 1;
        if (y >= h) y = 2 * h - y - 1;
        return in[y * w + x];
    }

    // Kirsch コンパスフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double max_response = 0;
            for (int k = 0; k < 8; k++) {
                double response = 0;
                for (int ky = -1; ky <= 1; ky++) {
                    for (int kx = -1; kx <= 1; kx++) {
                        response += kernels[k][ky + 1][kx + 1] * interpolate(x + kx, y + ky);
                    }
                }
                max_response = fmax(max_response, fabs(response));
            }
            out[y * w + x] = max_response;
        }
    }

    // 出力を画像の最大値で正規化
    double max_out = 0;
    for (int i = 0; i < h * w; i++) {
        max_out = fmax(max_out, out[i]);
    }
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_out;
    }
}
