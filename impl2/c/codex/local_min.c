#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x, yy, xx;

    /*
     * The specification does not define _k(a), so choose a square window
     * with radius r = 1 + floor(4*a), giving odd sizes from 3x3 to 11x11.
     *
     * Border handling is also unspecified; the window is clipped to the
     * image bounds (no padding).
     *
     * Input and output are assumed not to overlap, since aliasing behavior
     * is not specified by the contract.
     */
    int r = 1 + (int)floor(4.0 * a);
    double threshold = 0.7 - 0.4 * b;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double minimum = INFINITY;
            double value = in[y * w + x];
            int y0 = y - r;
            int y1 = y + r;
            int x0 = x - r;
            int x1 = x + r;

            if (y0 < 0) y0 = 0;
            if (x0 < 0) x0 = 0;
            if (y1 >= h) y1 = h - 1;
            if (x1 >= w) x1 = w - 1;

            for (yy = y0; yy <= y1; ++yy) {
                for (xx = x0; xx <= x1; ++xx) {
                    double v = in[yy * w + xx];
                    if (v < minimum)
                        minimum = v;
                }
            }

            out[y * w + x] =
                (value == minimum && value < threshold) ? 1.0 : 0.0;
        }
    }
}
