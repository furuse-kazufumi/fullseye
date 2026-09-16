#include <math.h>
#include <stdlib.h>

void fs2_apply(const double *in, int h, int w, double a, double b,
               double *out)
{
    double hist[64] = {0.0};
    double smooth[64];
    size_t n = (size_t)h * (size_t)w;
    size_t k;
    int i, j;
    int p1 = 0;
    int p2 = -1;
    int lo, hi, valley;
    double thr;

    (void)a;
    (void)b;

    /*
     * The specification does not define handling of values outside [0,1].
     * Finite out-of-range values and infinities are clamped to the nearest
     * endpoint bin. NaNs are assigned to bin 0 and compare false at output.
     */
    for (k = 0; k < n; ++k) {
        double v = in[k];
        int bin;

        if (isnan(v) || v <= 0.0) {
            bin = 0;
        } else if (v >= 1.0) {
            bin = 63;
        } else {
            bin = (int)(v * 64.0);
            if (bin < 0)
                bin = 0;
            else if (bin > 63)
                bin = 63;
        }
        hist[bin] += 1.0;
    }

    /*
     * The specification does not define Gaussian boundary handling or
     * truncation. Here the exact discrete Gaussian weights between all 64
     * bins are used, with unavailable bins omitted and the remaining weights
     * renormalized at each boundary.
     */
    for (i = 0; i < 64; ++i) {
        double weighted_sum = 0.0;
        double weight_sum = 0.0;

        for (j = 0; j < 64; ++j) {
            double d = (double)(i - j);
            double weight = exp(-(d * d) / (2.0 * 1.5 * 1.5));
            weighted_sum += hist[j] * weight;
            weight_sum += weight;
        }
        smooth[i] = weighted_sum / weight_sum;
    }

    /* Unspecified ties are resolved in favor of the lower-numbered bin. */
    for (i = 1; i < 64; ++i) {
        if (smooth[i] > smooth[p1])
            p1 = i;
    }

    for (i = 0; i < 64; ++i) {
        if (abs(i - p1) >= 5) {
            if (p2 < 0 || smooth[i] > smooth[p2])
                p2 = i;
        }
    }

    if (p2 < 0) {
        lo = 32;
        hi = 32;
    } else if (p1 < p2) {
        lo = p1;
        hi = p2;
    } else {
        lo = p2;
        hi = p1;
    }

    /*
     * "Between" is interpreted as including both endpoint bins.
     * Equal minima are resolved toward the lower bin.
     */
    valley = lo;
    for (i = lo + 1; i <= hi; ++i) {
        if (smooth[i] < smooth[valley])
            valley = i;
    }

    thr = (double)valley / 64.0;

    for (k = 0; k < n; ++k)
        out[k] = (in[k] > thr) ? 1.0 : 0.0;
}
