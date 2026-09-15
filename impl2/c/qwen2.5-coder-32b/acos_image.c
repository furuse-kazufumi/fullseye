#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用なので無視する
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double value = in[y * w + x];
            // 値域が [0,1] を想定するが、範囲外の値が来ても落ちないようクリッピングする
            if (value < 0.0) value = 0.0;
            if (value > 1.0) value = 1.0;
            // arccos(x) / π で [0,1] を [0,1] に写す
            out[y * w + x] = acos(value) / M_PI;
        }
    }
}
