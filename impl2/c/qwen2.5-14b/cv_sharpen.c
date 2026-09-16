#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を折り返す (BORDER_REFLECT_101) と指定されているため、
    // 画像の端の画素値を内部で適切に計算する。
    // 3x3 のカーネルを用いて畳み込みを行う。
    // カーネルは中心が 1+4a で、上下左右が -a となる。
    // a が 0 の場合は単位カーネル (1) となり、画像は変化しない。
    // a が 1 の場合は離散ラプラシアンカーネル (-1 -1 -1, -1 8 -1, -1 -1 -1) となる。

    // 画像の端の処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            // 3x3 のカーネルを適用
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // 端の処理
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 2;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 2;
                    // カーネルの値
                    double kernel = (ky == 0 && kx == 0) ? (1 + 4 * a) : -a;
                    sum += kernel * in[ny * w + nx];
                }
            }
            // 出力画像に結果を格納
            out[y * w + x] = fmin(1.0, fmax(0.0, sum));
        }
    }
}
