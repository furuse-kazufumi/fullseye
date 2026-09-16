#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 3x3 エンボスカーネル
    const double kernel[3][3] = {
        {-1, 0, 0},
        {0, 0, 0},
        {0, 1, 0}
    };

    // 出力画像の各ピクセルに対してカーネルを適用
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double sum = 0.0;
            for (int ky = 0; ky < 3; ky++) {
                for (int kx = 0; kx < 3; kx++) {
                    int iy = y + ky - 1;
                    int ix = x + kx - 1;
                    sum += kernel[ky][kx] * in[iy * w + ix];
                }
            }
            // 結果を出力画像に格納
            out[y * w + x] = sum;
        }
    }

    // 画像の端の処理
    // ここでは端のピクセルはそのままコピーする
    for (int y = 0; y < h; y++) {
        out[y * w] = in[y * w];
        out[y * w + w - 1] = in[y * w + w - 1];
    }
    for (int x = 0; x < w; x++) {
        out[x] = in[x];
        out[(h - 1) * w + x] = in[(h - 1) * w + x];
    }
}
