#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 端の扱い: 端画素を重複させて折り返す (d c b a | a b c d)
    // これは、画像の境界を反射的に延長することで実現される。
    // 画像の端の値は、その隣接する内部ピクセルの値を使用して計算される。

    int iterations = 1 + (int)(a * 8); // 反復回数
    double time_step = 0.0625; // 時間刻み

    // 画像の境界を反射的に延長するための一時的な配列を用意
    int padded_h = h + 2;
    int padded_w = w + 2;
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    double* padded_out = (double*)malloc(padded_h * padded_w * sizeof(double));

    // 入力画像を境界を含む配列にコピー
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // 境界の値を反射的に延長
    for (int x = 0; x < padded_w; ++x) {
        padded_in[x] = padded_in[x + 1];
        padded_in[(padded_h - 1) * padded_w + x] = padded_in[(padded_h - 2) * padded_w + x];
    }
    for (int y = 0; y < padded_h; ++y) {
        padded_in[y * padded_w] = padded_in[y * padded_w + 1];
        padded_in[y * padded_w + (padded_w - 1)] = padded_in[y * padded_w + (padded_w - 2)];
    }

    // 曲率流平滑化の反復処理
    for (int iter = 0; iter < iterations; ++iter) {
        for (int y = 1; y < padded_h - 1; ++y) {
            for (int x = 1; x < padded_w - 1; ++x) {
                double dx = (padded_in[(y + 1) * padded_w + x] - padded_in[(y - 1) * padded_w + x]) / 2.0;
                double dy = (padded_in[y * padded_w + (x + 1)] - padded_in[y * padded_w + (x - 1)]) / 2.0;
                double dxx = padded_in[(y + 1) * padded_w + x] - 2 * padded_in[y * padded_w + x] + padded_in[(y - 1) * padded_w + x];
                double dyy = padded_in[y * padded_w + (x + 1)] - 2 * padded_in[y * padded_w + x] + padded_in[y * padded_w + (x - 1)];
                double dxy = (padded_in[(y + 1) * padded_w + (x + 1)] - padded_in[(y + 1) * padded_w + (x - 1)] - padded_in[(y - 1) * padded_w + (x + 1)] + padded_in[(y - 1) * padded_w + (x - 1)]) / 4.0;
                double curvature = (dxx * dyy - dxy * dxy) / (sqrt(dxx * dxx + 2 * dxy * dxy + dyy * dyy) + 1e-6);
                double diffusion = time_step * curvature;
                padded_out[y * padded_w + x] = padded_in[y * padded_w + x] + diffusion * (dx * dx + dy * dy);
            }
        }

        // 一時的な配列を交換
        double* temp = padded_in;
        padded_in = padded_out;
        padded_out = temp;
    }

    // 出力画像に結果をコピー
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = fmin(fmax(padded_in[(y + 1) * padded_w + (x + 1)], 0.0), 1.0);
        }
    }

    // 動的確保したメモリを解放
    free(padded_in);
    free(padded_out);
}
