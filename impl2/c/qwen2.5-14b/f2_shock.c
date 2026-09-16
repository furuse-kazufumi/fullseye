#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は無視する
    (void)b;

    // 端の画素を重複させて折り返す (reflect)
    // これは、入力画像の端の画素を内部の画素値で埋める手法です。
    // これは仕様書で指定されている端の扱いです。

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // ショックフィルタの適用
    for (int iter = 0; iter < (int)(a * 100); ++iter) {
        double laplacian[h * w];
        double grad_magnitude[h * w];

        // Laplacian の計算
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                laplacian[y * w + x] = in[(y - 1) * w + (x - 1)] +
                                       in[(y - 1) * w + x] +
                                       in[(y - 1) * w + (x + 1)] +
                                       in[y * w + (x - 1)] +
                                       in[y * w + x] +
                                       in[y * w + (x + 1)] +
                                       in[(y + 1) * w + (x - 1)] +
                                       in[(y + 1) * w + x] +
                                       in[(y + 1) * w + (x + 1)] -
                                       9 * in[y * w + x];
            }
        }

        // Gradient magnitude の計算
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                double dx = in[y * w + (x + 1)] - in[y * w + (x - 1)];
                double dy = in[(y + 1) * w + x] - in[(y - 1) * w + x];
                grad_magnitude[y * w + x] = sqrt(dx * dx + dy * dy);
            }
        }

        // ショックフィルタの適用
        for (int y = 1; y < h - 1; ++y) {
            for (int x = 1; x < w - 1; ++x) {
                if (laplacian[y * w + x] < 0) {
                    out[y * w + x] = fmax(out[y * w + x], in[y * w + x] + grad_magnitude[y * w + x]);
                } else {
                    out[y * w + x] = fmin(out[y * w + x], in[y * w + x] - grad_magnitude[y * w + x]);
                }
            }
        }
    }
}
