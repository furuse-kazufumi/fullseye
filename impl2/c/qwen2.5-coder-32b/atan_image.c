#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用なので無視する
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = in[y * w + x];
            // arctan(x) / (π/2) で [0,1] を [0,1] に写す
            out[y * w + x] = atan(value) / (M_PI / 2.0);
        }
    }
}
