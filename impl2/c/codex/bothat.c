#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t n = (size_t)h * (size_t)w;
    double *dilated;
    double *closed;
    int k_index;
    int radius;
    int y, x, dy, dx;
    double maximum = 0.0;

    (void)b; /* b is unused by specification. */

    /*
     * The specification does not define boundary handling.
     * This implementation uses edge replication (coordinates outside the
     * image are clamped to the nearest valid pixel).
     */

    /* Map a to square sizes 3, 5, 7, and 9 at quarter intervals. */
    if (a < 0.25)
        k_index = 0;
    else if (a < 0.50)
        k_index = 1;
    else if (a < 0.75)
        k_index = 2;
    else
        k_index = 3;

    radius = k_index + 1;

    if ((size_t)w != 0 && (size_t)h > (size_t)-1 / (size_t)w) {
        return;
    }
    if (n > (size_t)-1 / sizeof(double)) {
        return;
    }

    dilated = (double *)malloc(n * sizeof(double));
    closed = (double *)malloc(n * sizeof(double));

    if (dilated == NULL || closed == NULL) {
        free(dilated);
        free(closed);
        memset(out, 0, n * sizeof(double));
        return;
    }

    /* Gray-scale dilation with a square structuring element. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int sy = y - radius;
            int sx = x - radius;
            double value;

            if (sy < 0)
                sy = 0;
            if (sx < 0)
                sx = 0;

            value = in[(size_t)sy * (size_t)w + (size_t)sx];

            for (dy = -radius; dy <= radius; ++dy) {
                sy = y + dy;
                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    double sample;

                    sx = x + dx;
                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    sample = in[(size_t)sy * (size_t)w + (size_t)sx];
                    if (sample > value)
                        value = sample;
                }
            }

            dilated[(size_t)y * (size_t)w + (size_t)x] = value;
        }
    }

    /* Gray-scale erosion of the dilation, completing the closing. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int sy = y - radius;
            int sx = x - radius;
            double value;

            if (sy < 0)
                sy = 0;
            if (sx < 0)
                sx = 0;

            value = dilated[(size_t)sy * (size_t)w + (size_t)sx];

            for (dy = -radius; dy <= radius; ++dy) {
                sy = y + dy;
                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    double sample;

                    sx = x + dx;
                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    sample =
                        dilated[(size_t)sy * (size_t)w + (size_t)sx];
                    if (sample < value)
                        value = sample;
                }
            }

            closed[(size_t)y * (size_t)w + (size_t)x] = value;
        }
    }

    /* Bottom hat: closing minus the original image. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t i = (size_t)y * (size_t)w + (size_t)x;
            double value = closed[i] - in[i];

            /* Suppress negative round-off from the extensive closing. */
            if (value < 0.0)
                value = 0.0;

            closed[i] = value;
            if (value > maximum)
                maximum = value;
        }
    }

    /* Normalize by this image's maximum; an all-zero result stays zero. */
    if (maximum > 0.0) {
        size_t i;
        for (i = 0; i < n; ++i)
            out[i] = closed[i] / maximum;
    } else {
        memset(out, 0, n * sizeof(double));
    }

    free(closed);
    free(dilated);
}
