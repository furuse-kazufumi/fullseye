#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t n;
    double *eroded;
    double *opened;
    int radius;
    int size;
    int y, x, dy, dx;
    double max_value = 0.0;

    (void)b;

    n = (size_t)h * (size_t)w;
    radius = 1 + (int)(a * 3.0);
    size = 2 * radius + 1;

    eroded = (double *)malloc(n * sizeof(double));
    opened = (double *)malloc(n * sizeof(double));

    if (eroded == NULL || opened == NULL) {
        free(eroded);
        free(opened);
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                out[(size_t)y * (size_t)w + (size_t)x] = 0.0;
            }
        }
        return;
    }

    /*
     * The specification does not define the exact rasterization of the
     * elliptical structuring element. This implementation includes samples
     * whose normalized squared distance from the center is at most 1.
     *
     * The specification also does not define border handling. Coordinates
     * outside the image are clamped to the nearest border pixel (replication).
     */

    /* Erosion. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double v = 0.0;
            int have_value = 0;

            for (dy = -radius; dy <= radius; ++dy) {
                int sy;
                double ny = (double)dy / (double)radius;

                if (dy * dy > radius * radius)
                    continue;

                sy = y + dy;
                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    int sx;
                    double nx = (double)dx / (double)radius;
                    double sample;

                    if (nx * nx + ny * ny > 1.0)
                        continue;

                    sx = x + dx;
                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    sample = in[(size_t)sy * (size_t)w + (size_t)sx];

                    /* NaNs are ignored; an all-NaN neighborhood becomes 0. */
                    if (isnan(sample))
                        continue;

                    if (!have_value || sample < v) {
                        v = sample;
                        have_value = 1;
                    }
                }
            }

            eroded[(size_t)y * (size_t)w + (size_t)x] =
                have_value ? v : 0.0;
        }
    }

    /* Dilation of the erosion: grayscale opening. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double v = 0.0;
            int have_value = 0;

            for (dy = -radius; dy <= radius; ++dy) {
                int sy;
                double ny = (double)dy / (double)radius;

                if (dy * dy > radius * radius)
                    continue;

                sy = y + dy;
                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    int sx;
                    double nx = (double)dx / (double)radius;
                    double sample;

                    if (nx * nx + ny * ny > 1.0)
                        continue;

                    sx = x + dx;
                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    sample = eroded[(size_t)sy * (size_t)w + (size_t)sx];

                    if (isnan(sample))
                        continue;

                    if (!have_value || sample > v) {
                        v = sample;
                        have_value = 1;
                    }
                }
            }

            opened[(size_t)y * (size_t)w + (size_t)x] =
                have_value ? v : 0.0;
        }
    }

    /* Top-hat difference and determination of its normalization maximum. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t i = (size_t)y * (size_t)w + (size_t)x;
            double v = in[i] - opened[i];

            /*
             * Mathematical opening is anti-extensive, but floating-point
             * anomalies can produce negative or NaN differences.
             */
            if (isnan(v) || v < 0.0)
                v = 0.0;

            opened[i] = v;
            if (v > max_value)
                max_value = v;
        }
    }

    if (max_value > 0.0 && isfinite(max_value)) {
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                size_t i = (size_t)y * (size_t)w + (size_t)x;
                out[i] = opened[i] / max_value;
            }
        }
    } else if (isinf(max_value)) {
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                size_t i = (size_t)y * (size_t)w + (size_t)x;
                out[i] = isinf(opened[i]) ? 1.0 : 0.0;
            }
        }
    } else {
        memset(out, 0, n * sizeof(double));
    }

    free(opened);
    free(eroded);

    (void)size;
}
