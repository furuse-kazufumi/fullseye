#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。ヘシアン行列に基づく応答を計算する。
    // 端の画素は最近傍法で複製する。

    // ヘシアン行列の成分を計算するためのカーネル
    double kernel[3][3] = {
        {1, 0, -1},
        {2, 0, -2},
        {1, 0, -1}
    };

    // 出力画像の最大値を初期化
    double max_response = 0.0;

    // 各画素についてヘシアン行列の応答を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double Ixx = 0.0, Ixy = 0.0, Iyy = 0.0;

            // ヘシアン行列の成分を計算
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int iy = y + ky, ix = x + kx;
                    // 端の画素は最近傍法で複製
                    if (iy < 0) iy = 0;
                    if (iy >= h) iy = h - 1;
                    if (ix < 0) ix = 0;
                    if (ix >= w) ix = w - 1;

                    double Ix = kernel[0][kx + 1] * in[iy * w + ix];
                    double Iy = kernel[ky + 1][0] * in[iy * w + ix];

                    Ixx += Ix * Ix;
                    Ixy += Ix * Iy;
                    Iyy += Iy * Iy;
                }
            }

            // ヘシアン行列の応答を計算
            double response = sqrt(Ixx * Iyy - Ixy * Ixy);
            out[y * w + x] = response;

            // 最大応答を更新
            if (response > max_response) {
                max_response = response;
            }
        }
    }

    // 出力を最大応答で正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_response;
    }
}
