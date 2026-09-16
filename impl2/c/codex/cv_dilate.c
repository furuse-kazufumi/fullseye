#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int radius;
    int y, x, ky;

    (void)b; /* b is unused by specification. */

    radius = 1 + (int)(a * 3.0); /* Kernel size: 2*radius+1, i.e. 3..9. */

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double maximum = in[y * w + x];

            for (ky = -radius; ky <= radius; ++ky) {
                int yy = y + ky;
                double ratio;
                int half_width;
                int kx;

                /*
                 * The specification does not define border padding.
                 * This implementation clips the structuring element at image
                 * boundaries (equivalent to padding with negative infinity).
                 */
                if (yy < 0 || yy >= h)
                    continue;

                ratio = 1.0 -
                        ((double)ky * (double)ky) /
                        ((double)radius * (double)radius);

                half_width = (int)floor(
                    (double)radius * sqrt(ratio < 0.0 ? 0.0 : ratio) + 0.5
                );

                for (kx = -half_width; kx <= half_width; ++kx) {
                    int xx = x + kx;
                    double value;

                    if (xx < 0 || xx >= w)
                        continue;

                    value = in[yy * w + xx];
                    if (value > maximum)
                        maximum = value;
                }
            }

            out[y * w + x] = maximum;
        }
    }
}
