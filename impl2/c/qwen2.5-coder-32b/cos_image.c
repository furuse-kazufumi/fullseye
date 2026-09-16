#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b are unused parameters as per the specification.
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double value = in[y * w + x];
            // Apply the cosine transformation as specified: (cos(2πx) + 1) / 2
            // Here, x is the pixel value in the range [0, 1].
            out[y * w + x] = (cos(2 * M_PI * value) + 1) / 2.0;
        }
    }
}
