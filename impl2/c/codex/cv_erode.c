#include <math.h>

void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y, x, ky, kx;
    int size = 3 + 2 * (int)(a * 3.0);
    int radius = size / 2;

    (void)b; /* b is unused by specification. */

    /*
     * Unspecified choices:
     * - Pixels outside the image are ignored (equivalent to +infinity padding
     *   for erosion).
     * - The ellipse is rasterized row by row using a rounded half-width.
     * - in and out are assumed not to overlap.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double minimum = in[y * w + x];

            for (ky = -radius; ky <= radius; ++ky) {
                int yy = y + ky;
                double ratio;
                int half_width;

                if (yy < 0 || yy >= h)
                    continue;

                ratio = 1.0 -
                        ((double)ky * (double)ky) /
                        ((double)radius * (double)radius);
                if (ratio < 0.0)
                    ratio = 0.0;

                half_width = (int)(radius * sqrt(ratio) + 0.5);

                for (kx = -half_width; kx <= half_width; ++kx) {
                    int xx = x + kx;
                    double value;

                    if (xx < 0 || xx >= w)
                        continue;

                    value = in[yy * w + xx];
                    if (value < minimum)
                        minimum = value;
                }
            }

            out[y * w + x] = minimum;
        }
    }
}
