#include <math.h>
#include <stdlib.h>
#include <string.h>

static int fs2_reflect_index(int i, int n)
{
    int period;
    int r;

    if (n <= 1)
        return 0;

    /* Unspecified boundary rule: use half-sample symmetric reflection. */
    period = 2 * n;
    r = i % period;
    if (r < 0)
        r += period;
    return (r < n) ? r : (period - 1 - r);
}

void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y, x, dy, dx;
    int radius, k;
    double offset;
    double area;

    /*
     * The specification does not define _k(a). Choose an odd window size
     * from 3 through 31, rounded to the nearest available size:
     *     radius = 1 + round(14*a), k = 2*radius + 1.
     *
     * Foreground polarity is also not explicit; choose bright foreground:
     * input > local_mean + offset.
     *
     * in and out are assumed not to overlap.
     */
    radius = 1 + (int)floor(14.0 * a + 0.5);
    if (radius < 1)
        radius = 1;
    else if (radius > 15)
        radius = 15;

    k = 2 * radius + 1;
    area = (double)k * (double)k;
    offset = (b - 0.5) * 0.4;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double sum = 0.0;
            double mean;

            for (dy = -radius; dy <= radius; ++dy) {
                int sy = fs2_reflect_index(y + dy, h);

                for (dx = -radius; dx <= radius; ++dx) {
                    int sx = fs2_reflect_index(x + dx, w);
                    sum += in[(size_t)sy * (size_t)w + (size_t)sx];
                }
            }

            mean = sum / area;
            out[(size_t)y * (size_t)w + (size_t)x] =
                (in[(size_t)y * (size_t)w + (size_t)x] >
                 mean + offset) ? 1.0 : 0.0;
        }
    }
}
