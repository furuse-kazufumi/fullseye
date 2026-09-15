#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は使用しない
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int index = y * w + x;
            double clipped_value = (in[index] < 0.0) ? 0.0 : (in[index] > 1.0) ? 1.0 : in[index];
            out[index] = pow(clipped_value, a);
        }
    }
}
