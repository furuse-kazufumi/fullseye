#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x;

    (void)a;
    (void)b;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            const int i = y * w + x;
            out[i] = fabs(in[i]);
        }
    }
}
