#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int total_pixels = h * w;
    int* histogram = (int*)calloc(256, sizeof(int));
    double* cumulative_sum = (double*)calloc(256, sizeof(double));
    double* cumulative_sum_sq = (double*)calloc(256, sizeof(double));

    // Build histogram
    for (int i = 0; i < total_pixels; i++) {
        int pixel_value = (int)(in[i] * 255.0);
        if (pixel_value < 0) pixel_value = 0;
        if (pixel_value > 255) pixel_value = 255;
        histogram[pixel_value]++;
    }

    // Calculate cumulative sums and sums of squares
    cumulative_sum[0] = histogram[0];
    cumulative_sum_sq[0] = histogram[0] * 0.0;
    for (int i = 1; i < 256; i++) {
        cumulative_sum[i] = cumulative_sum[i - 1] + histogram[i];
        cumulative_sum_sq[i] = cumulative_sum_sq[i - 1] + histogram[i] * i;
    }

    // Otsu's method to find the threshold
    double max_variance = 0.0;
    int threshold = 0;
    for (int t = 0; t < 256; t++) {
        double w0 = cumulative_sum[t] / total_pixels;
        double w1 = 1.0 - w0;
        if (w0 == 0 || w1 == 0) continue;

        double mean0 = cumulative_sum_sq[t] / cumulative_sum[t];
        double mean1 = (cumulative_sum_sq[255] - cumulative_sum_sq[t]) / (cumulative_sum[255] - cumulative_sum[t]);
        double variance = w0 * w1 * (mean0 - mean1) * (mean0 - mean1);

        if (variance > max_variance) {
            max_variance = variance;
            threshold = t;
        }
    }

    // Apply threshold
    for (int i = 0; i < total_pixels; i++) {
        int pixel_value = (int)(in[i] * 255.0);
        if (pixel_value < 0) pixel_value = 0;
        if (pixel_value > 255) pixel_value = 255;
        out[i] = (pixel_value > threshold) ? 1.0 : 0.0;
    }

    // Free allocated memory
    free(histogram);
    free(cumulative_sum);
    free(cumulative_sum_sq);
}
