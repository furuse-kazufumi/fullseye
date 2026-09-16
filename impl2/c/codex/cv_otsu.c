#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    double hist[256] = {0.0};
    double total;
    double sum_all = 0.0;
    double sum_bg = 0.0;
    double count_bg = 0.0;
    double best_variance = 0.0;
    int threshold = 0;
    int n = h * w;
    int i;

    (void)a;
    (void)b;

    /*
     * The specification does not define the exact float-to-u8 rounding rule.
     * This implementation clips to [0,1], multiplies by 255, and truncates
     * toward zero. NaN is mapped to 0; infinities are clipped to an endpoint.
     */
    for (i = 0; i < n; ++i) {
        double v = in[i];
        int q;

        if (v != v || v <= 0.0)
            q = 0;
        else if (v >= 1.0)
            q = 255;
        else
            q = (int)(v * 255.0);

        hist[q] += 1.0;
    }

    total = (double)n;

    for (i = 0; i < 256; ++i)
        sum_all += (double)i * hist[i];

    /*
     * OpenCV-style Otsu selection: retain the first threshold attaining the
     * maximum between-class variance, then classify values strictly greater
     * than that threshold as foreground (THRESH_BINARY).
     */
    for (i = 0; i < 256; ++i) {
        double count_fg;
        double mean_bg;
        double mean_fg;
        double delta;
        double variance;

        count_bg += hist[i];
        sum_bg += (double)i * hist[i];
        count_fg = total - count_bg;

        if (count_bg <= 0.0)
            continue;
        if (count_fg <= 0.0)
            break;

        mean_bg = sum_bg / count_bg;
        mean_fg = (sum_all - sum_bg) / count_fg;
        delta = mean_bg - mean_fg;
        variance = count_bg * count_fg * delta * delta;

        if (variance > best_variance) {
            best_variance = variance;
            threshold = i;
        }
    }

    for (i = 0; i < n; ++i) {
        double v = in[i];
        int q;

        if (v != v || v <= 0.0)
            q = 0;
        else if (v >= 1.0)
            q = 255;
        else
            q = (int)(v * 255.0);

        out[i] = (q > threshold) ? 1.0 : 0.0;
    }
}
