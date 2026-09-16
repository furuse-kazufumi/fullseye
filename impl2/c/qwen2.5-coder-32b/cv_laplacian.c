#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 3x3 ラプラシアンカーネル: 0 -1 0
    //                           -1  4 -1
    //                            0 -1 0
    // 端の扱い: 端画素を重複させずに折り返す (BORDER_REFLECT_101)

    int x, y;
    double laplacian_value;
    double max_value = 0.0;

    for (y = 0; y < h; y++) {
        for (x = 0; x < w; x++) {
            double pixel = in[y * w + x];
            double top = (y > 0) ? in[(y - 1) * w + x] : in[(y + 1) * w + x];
            double bottom = (y < h - 1) ? in[(y + 1) * w + x] : in[(y - 1) * w + x];
            double left = (x > 0) ? in[y * w + (x - 1)] : in[y * w + (x + 1)];
            double right = (x < w - 1) ? in[y * w + (x + 1)] : in[y * w + (x - 1)];

            laplacian_value = 4 * pixel - top - bottom - left - right;

            // 最大値を記録
            if (fabs(laplacian_value) > max_value) {
                max_value = fabs(laplacian_value);
            }

            out[y * w + x] = laplacian_value;
        }
    }

    // 正規化
    if (max_value > 0.0) {
        for (y = 0; y < h; y++) {
            for (x = 0; x < w; x++) {
                out[y * w + x] = 0.5 + (out[y * w + x] / (2 * max_value));
            }
        }
    }
}
