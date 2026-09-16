#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t n = (size_t)h * (size_t)w;
    unsigned char *cluster = NULL;
    unsigned char *boundary = NULL;
    double *source = NULL;
    double *temp = NULL;
    double *conc = NULL;
    double *kernel = NULL;
    int generations;
    int radius;
    int kernel_size;
    double sigma = 2.0; /* Unspecified: use a fixed Gaussian sigma of 2 pixels. */
    double maximum;
    size_t brightest = 0;
    size_t i;
    int generation;

    /*
     * Unspecified choices:
     * - Non-finite input samples are treated as zero.
     * - Gaussian convolution uses reflected/clamped edge extension.
     * - The Gaussian is truncated at three standard deviations.
     * - Boundary threshold = min + b * (max - min), so b=0 attaches
     *   the full boundary and b=1 attaches only concentration maxima.
     */

    if (n == 0 || n > ((size_t)-1) / sizeof(double)) {
        return;
    }

    for (i = 0; i < n; ++i) {
        out[i] = 0.0;
    }

    cluster = (unsigned char *)calloc(n, sizeof(unsigned char));
    boundary = (unsigned char *)calloc(n, sizeof(unsigned char));
    source = (double *)malloc(n * sizeof(double));
    temp = (double *)malloc(n * sizeof(double));
    conc = (double *)malloc(n * sizeof(double));

    radius = (int)ceil(3.0 * sigma);
    kernel_size = 2 * radius + 1;
    kernel = (double *)malloc((size_t)kernel_size * sizeof(double));

    if (cluster == NULL || boundary == NULL || source == NULL ||
        temp == NULL || conc == NULL || kernel == NULL) {
        free(cluster);
        free(boundary);
        free(source);
        free(temp);
        free(conc);
        free(kernel);
        return;
    }

    maximum = isfinite(in[0]) ? in[0] : 0.0;
    for (i = 0; i < n; ++i) {
        double v = isfinite(in[i]) ? in[i] : 0.0;
        source[i] = v;
        if (v > maximum) {
            maximum = v;
            brightest = i;
        }
    }

    {
        double seed_threshold = 0.75 * maximum;
        for (i = 0; i < n; ++i) {
            if (source[i] >= seed_threshold) {
                cluster[i] = 1;
            }
        }
        cluster[brightest] = 1;
    }

    {
        double sum = 0.0;
        int k;
        for (k = -radius; k <= radius; ++k) {
            double x = (double)k;
            double value = exp(-(x * x) / (2.0 * sigma * sigma));
            kernel[k + radius] = value;
            sum += value;
        }
        for (k = 0; k < kernel_size; ++k) {
            kernel[k] /= sum;
        }
    }

    generations = 1 + (int)(11.0 * a);

    for (generation = 0; generation < generations; ++generation) {
        int y, x, k;
        int have_boundary = 0;
        double boundary_min = 0.0;
        double boundary_max = 0.0;
        size_t strongest = 0;

        for (i = 0; i < n; ++i) {
            conc[i] = cluster[i] ? 0.0 : source[i];
            boundary[i] = 0;
        }

        /* Horizontal Gaussian pass with clamped edge extension. */
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                double sum = 0.0;
                for (k = -radius; k <= radius; ++k) {
                    int xx = x + k;
                    if (xx < 0)
                        xx = 0;
                    else if (xx >= w)
                        xx = w - 1;
                    sum += conc[(size_t)y * (size_t)w + (size_t)xx]
                         * kernel[k + radius];
                }
                temp[(size_t)y * (size_t)w + (size_t)x] = sum;
            }
        }

        /* Vertical Gaussian pass with clamped edge extension. */
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                double sum = 0.0;
                for (k = -radius; k <= radius; ++k) {
                    int yy = y + k;
                    if (yy < 0)
                        yy = 0;
                    else if (yy >= h)
                        yy = h - 1;
                    sum += temp[(size_t)yy * (size_t)w + (size_t)x]
                         * kernel[k + radius];
                }
                conc[(size_t)y * (size_t)w + (size_t)x] = sum;
            }
        }

        /* Find the unclaimed Moore boundary of the current cluster. */
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                size_t p = (size_t)y * (size_t)w + (size_t)x;
                int dy, dx;
                int adjacent = 0;

                if (cluster[p])
                    continue;

                for (dy = -1; dy <= 1 && !adjacent; ++dy) {
                    int yy = y + dy;
                    if (yy < 0 || yy >= h)
                        continue;
                    for (dx = -1; dx <= 1; ++dx) {
                        int xx = x + dx;
                        if ((dx == 0 && dy == 0) || xx < 0 || xx >= w)
                            continue;
                        if (cluster[(size_t)yy * (size_t)w + (size_t)xx]) {
                            adjacent = 1;
                            break;
                        }
                    }
                }

                if (adjacent) {
                    boundary[p] = 1;
                    if (!have_boundary || conc[p] > boundary_max) {
                        boundary_max = conc[p];
                        strongest = p;
                    }
                    if (!have_boundary || conc[p] < boundary_min) {
                        boundary_min = conc[p];
                    }
                    have_boundary = 1;
                }
            }
        }

        if (!have_boundary)
            break;

        {
            double threshold =
                boundary_min + b * (boundary_max - boundary_min);

            for (i = 0; i < n; ++i) {
                if (boundary[i] && conc[i] >= threshold) {
                    cluster[i] = 1;
                }
            }

            /* Required guarantee: at least the strongest boundary cell sticks. */
            cluster[strongest] = 1;
        }
    }

    for (i = 0; i < n; ++i) {
        out[i] = cluster[i] ? 1.0 : 0.0;
    }

    free(cluster);
    free(boundary);
    free(source);
    free(temp);
    free(conc);
    free(kernel);
}
