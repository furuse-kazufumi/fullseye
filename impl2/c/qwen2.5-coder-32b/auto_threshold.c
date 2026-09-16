#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int size = h * w;
    int* histogram = (int*)calloc(256, sizeof(int));
    double* cumulative_sum = (double*)calloc(256, sizeof(double));
    double* cumulative_sum_sq = (double*)calloc(256, sizeof(double));
    double* cumulative_count = (double*)calloc(256, sizeof(double));

    // Build histogram
    for (int i = 0; i < size; i++) {
        int bin = (int)(in[i] * 255.0);
        if (bin < 0) bin = 0;
        if (bin > 255) bin = 255;
        histogram[bin]++;
    }

    // Calculate cumulative sums and counts
    for (int i = 0; i < 256; i++) {
        cumulative_count[i] = (i == 0) ? histogram[i] : cumulative_count[i - 1] + histogram[i];
        cumulative_sum[i] = (i == 0) ? histogram[i] * i : cumulative_sum[i - 1] + histogram[i] * i;
        cumulative_sum_sq[i] = (i == 0) ? histogram[i] * i * i : cumulative_sum_sq[i - 1] + histogram[i] * i * i;
    }

    // Otsu's method to find the threshold
    double max_variance = 0.0;
    int threshold = 0;
    for (int i = 0; i < 256; i++) {
        double w0 = cumulative_count[i] / size;
        double w1 = 1.0 - w0;
        if (w0 == 0 || w1 == 0) continue;

        double mean0 = cumulative_sum[i] / cumulative_count[i];
        double mean1 = (cumulative_sum[255] - cumulative_sum[i]) / (size - cumulative_count[i]);
        double variance = w0 * w1 * (mean0 - mean1) * (mean0 - mean1);

        if (variance > max_variance) {
            max_variance = variance;
            threshold = i;
        }
    }

    // Apply threshold
    for (int i = 0; i < size; i++) {
        out[i] = (in[i] * 255.0 > threshold) ? 1.0 : 0.0;
    }

    // Free allocated memory
    free(histogram);
    free(cumulative_sum);
    free(cumulative_sum_sq);
    free(cumulative_count);
}
