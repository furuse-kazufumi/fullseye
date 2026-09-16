#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    enum { BINS = 256 };
    size_t hist[BINS] = {0};
    size_t n = (size_t)h * (size_t)w;
    size_t valid_count = 0;
    size_t i;
    double min_value = 0.0;
    double max_value = 0.0;
    double scale;
    double lo;
    double hi;
    double bin_width;
    double threshold;
    int first_value = 1;
    int k;
    int best_k = 0;
    double best_variance = -1.0;
    double total_moment = 0.0;
    double lower_moment = 0.0;
    size_t lower_count = 0;

    (void)a;
    (void)b;

    /*
     * The specification does not define handling of NaN or infinity.
     * This implementation excludes non-finite values from threshold
     * estimation and always emits background (0.0) for them.
     */
    for (i = 0; i < n; ++i) {
        double v = in[i];

        if (!isfinite(v))
            continue;

        if (first_value) {
            min_value = v;
            max_value = v;
            first_value = 0;
        } else {
            if (v < min_value)
                min_value = v;
            if (v > max_value)
                max_value = v;
        }
        ++valid_count;
    }

    if (valid_count == 0) {
        for (i = 0; i < n; ++i)
            out[i] = 0.0;
        return;
    }

    /*
     * For a constant image, Otsu's threshold is chosen as that constant.
     * Since foreground is defined as strictly brighter than the threshold,
     * the resulting region is empty.
     */
    if (min_value == max_value) {
        for (i = 0; i < n; ++i)
            out[i] = 0.0;
        return;
    }

    /*
     * The specification does not prescribe histogram resolution.
     * This implementation uses 256 equal-width bins over the finite
     * image minimum-to-maximum range and uses bin centers as thresholds.
     *
     * Values are scaled first so that extreme finite inputs cannot make
     * max_value - min_value overflow.
     */
    scale = fmax(fabs(min_value), fabs(max_value));
    lo = min_value / scale;
    hi = max_value / scale;
    bin_width = (hi - lo) / (double)BINS;

    for (i = 0; i < n; ++i) {
        double v = in[i];
        double z;
        double position;
        int bin;

        if (!isfinite(v))
            continue;

        z = v / scale;
        position = (z - lo) / (hi - lo);
        bin = (int)(position * (double)BINS);

        if (bin < 0)
            bin = 0;
        else if (bin >= BINS)
            bin = BINS - 1;

        ++hist[bin];
    }

    for (k = 0; k < BINS; ++k) {
        double center = lo + ((double)k + 0.5) * bin_width;
        total_moment += (double)hist[k] * center;
    }

    for (k = 0; k < BINS - 1; ++k) {
        size_t upper_count;
        double center;
        double lower_mean;
        double upper_mean;
        double difference;
        double variance;

        center = lo + ((double)k + 0.5) * bin_width;
        lower_count += hist[k];
        lower_moment += (double)hist[k] * center;
        upper_count = valid_count - lower_count;

        if (lower_count == 0 || upper_count == 0)
            continue;

        lower_mean = lower_moment / (double)lower_count;
        upper_mean =
            (total_moment - lower_moment) / (double)upper_count;
        difference = lower_mean - upper_mean;
        variance = (double)lower_count * (double)upper_count
                 * difference * difference;

        /* Ties are resolved in favor of the lowest threshold. */
        if (variance > best_variance) {
            best_variance = variance;
            best_k = k;
        }
    }

    threshold = lo + ((double)best_k + 0.5) * bin_width;

    for (i = 0; i < n; ++i) {
        double v = in[i];

        if (!isfinite(v))
            out[i] = 0.0;
        else
            out[i] = ((v / scale) > threshold) ? 1.0 : 0.0;
    }
}
