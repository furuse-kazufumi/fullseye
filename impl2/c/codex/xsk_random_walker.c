#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t n, i;
    unsigned char *marker = NULL;
    unsigned char *label = NULL;
    double *value = NULL;
    double dark_threshold;
    double bright_threshold;
    double beta;
    int dark_count = 0;
    int bright_count = 0;
    int iteration;
    const int max_iterations = 10000;
    const double tolerance = 1.0e-8;

    if (in == NULL || out == NULL || h < 1 || w < 1)
        return;

    n = (size_t)h * (size_t)w;

    marker = (unsigned char *)malloc(n * sizeof(*marker));
    label = (unsigned char *)malloc(n * sizeof(*label));
    value = (double *)malloc(n * sizeof(*value));

    if (marker == NULL || label == NULL || value == NULL) {
        /*
         * Allocation-failure behavior is not specified.  This implementation
         * returns an empty region so that every output element is still valid.
         */
        for (i = 0; i < n; ++i)
            out[i] = 0.0;
        free(marker);
        free(label);
        free(value);
        return;
    }

    dark_threshold = 0.3 + 0.2 * a;
    bright_threshold = 0.7 - 0.2 * a;
    beta = 10.0 + 200.0 * b;

    for (i = 0; i < n; ++i) {
        double v = in[i];

        /*
         * Handling of non-finite and out-of-range input is unspecified.
         * Clamp finite values to [0,1], and treat NaN as neutral gray.
         */
        if (v != v)
            v = 0.5;
        else if (v < 0.0)
            v = 0.0;
        else if (v > 1.0)
            v = 1.0;

        if (v < dark_threshold) {
            marker[i] = 1;
            value[i] = 0.0;
            ++dark_count;
        } else if (v > bright_threshold) {
            marker[i] = 2;
            value[i] = 1.0;
            ++bright_count;
        } else {
            marker[i] = 0;
            value[i] = 0.5;
        }
    }

    if (dark_count != 0 && bright_count != 0) {
        /*
         * The specification does not prescribe the numerical linear solver.
         * Weighted Gauss-Seidel relaxation is used to solve the discrete
         * harmonic random-walker probabilities on a 4-connected graph.
         */
        for (iteration = 0; iteration < max_iterations; ++iteration) {
            double max_change = 0.0;
            int y, x;

            for (y = 0; y < h; ++y) {
                for (x = 0; x < w; ++x) {
                    size_t p = (size_t)y * (size_t)w + (size_t)x;
                    double center;
                    double weighted_sum = 0.0;
                    double weight_sum = 0.0;
                    double new_value;
                    double change;

                    if (marker[p] != 0)
                        continue;

                    center = in[p];
                    if (center != center)
                        center = 0.5;
                    else if (center < 0.0)
                        center = 0.0;
                    else if (center > 1.0)
                        center = 1.0;

#define FS2_ADD_NEIGHBOR(q_)                                                \
                    do {                                                    \
                        size_t q = (q_);                                    \
                        double neighbor = in[q];                            \
                        double difference;                                  \
                        double weight;                                      \
                        if (neighbor != neighbor)                           \
                            neighbor = 0.5;                                 \
                        else if (neighbor < 0.0)                            \
                            neighbor = 0.0;                                 \
                        else if (neighbor > 1.0)                            \
                            neighbor = 1.0;                                 \
                        difference = center - neighbor;                     \
                        weight = exp(-beta * difference * difference);      \
                        weighted_sum += weight * value[q];                  \
                        weight_sum += weight;                               \
                    } while (0)

                    if (x > 0)
                        FS2_ADD_NEIGHBOR(p - 1);
                    if (x + 1 < w)
                        FS2_ADD_NEIGHBOR(p + 1);
                    if (y > 0)
                        FS2_ADD_NEIGHBOR(p - (size_t)w);
                    if (y + 1 < h)
                        FS2_ADD_NEIGHBOR(p + (size_t)w);

#undef FS2_ADD_NEIGHBOR

                    /*
                     * Image edges have no outside neighbors (a no-flux graph
                     * boundary), since edge padding is unspecified.
                     */
                    if (weight_sum > 0.0) {
                        new_value = weighted_sum / weight_sum;
                        change = fabs(new_value - value[p]);
                        value[p] = new_value;
                        if (change > max_change)
                            max_change = change;
                    }
                }
            }

            if (max_change < tolerance)
                break;
        }

        for (i = 0; i < n; ++i)
            label[i] = (unsigned char)(value[i] >= 0.5);
    } else {
        /*
         * A one-class marker set has no two-class random-walker solution.
         * The unspecified degenerate case is defined as one uniform label,
         * which consequently produces an empty boundary region.
         */
        memset(label, dark_count != 0 ? 0 : 1, n * sizeof(*label));
    }

    for (i = 0; i < n; ++i)
        out[i] = 0.0;

    /*
     * Boundary convention is unspecified.  Use a 4-connected, two-sided
     * boundary: both pixels of every horizontally or vertically adjacent
     * pair with different labels are included in the output region.
     */
    {
        int y, x;

        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                size_t p = (size_t)y * (size_t)w + (size_t)x;

                if (x + 1 < w) {
                    size_t q = p + 1;
                    if (label[p] != label[q]) {
                        out[p] = 1.0;
                        out[q] = 1.0;
                    }
                }

                if (y + 1 < h) {
                    size_t q = p + (size_t)w;
                    if (label[p] != label[q]) {
                        out[p] = 1.0;
                        out[q] = 1.0;
                    }
                }
            }
        }
    }

    free(marker);
    free(label);
    free(value);
}
