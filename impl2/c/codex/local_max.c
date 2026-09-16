#include <math.h>
#include <stddef.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x;
    int radius;
    double threshold = 0.3 + 0.4 * b;

    /*
     * The specification does not define _k(a). This implementation chooses
     * an odd square window with radius floor(1 + 7*a), giving sizes 3..17.
     */
    radius = 1 + (int)floor(7.0 * a);

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t index = (size_t)y * (size_t)w + (size_t)x;
            double value = in[index];
            double maximum = -HUGE_VAL;
            int y0 = y - radius;
            int y1 = y + radius;
            int x0 = x - radius;
            int x1 = x + radius;
            int yy, xx;

            /*
             * Border handling is unspecified. The window is clipped to the
             * image bounds; no values are synthesized outside the image.
             */
            if (y0 < 0) y0 = 0;
            if (x0 < 0) x0 = 0;
            if (y1 >= h) y1 = h - 1;
            if (x1 >= w) x1 = w - 1;

            for (yy = y0; yy <= y1; ++yy) {
                for (xx = x0; xx <= x1; ++xx) {
                    double candidate =
                        in[(size_t)yy * (size_t)w + (size_t)xx];

                    /* NaNs are ignored and are never considered maxima. */
                    if (!isnan(candidate) && candidate > maximum)
                        maximum = candidate;
                }
            }

            out[index] =
                (!isnan(value) && value == maximum && value > threshold)
                    ? 1.0
                    : 0.0;
        }
    }
}
