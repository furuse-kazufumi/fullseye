#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int size = h * w;
    int bins = 64;
    double histogram[64] = {0.0};
    double bin_width = 1.0 / bins;

    // Calculate histogram
    for (int i = 0; i < size; i++) {
        int bin_index = (int)(in[i] / bin_width);
        if (bin_index >= bins) bin_index = bins - 1; // Clamp to last bin if out of range
        histogram[bin_index]++;
    }

    // Smooth histogram with Gaussian kernel (sigma = 1.5)
    double gaussian_kernel[64] = {0.0};
    double sigma = 1.5;
    double sum = 0.0;
    for (int i = 0; i < bins; i++) {
        double x = (i - bins / 2) * bin_width;
        gaussian_kernel[i] = exp(-0.5 * (x * x) / (sigma * sigma));
        sum += gaussian_kernel[i];
    }
    for (int i = 0; i < bins; i++) {
        gaussian_kernel[i] /= sum;
    }

    double smoothed_histogram[64] = {0.0};
    for (int i = 0; i < bins; i++) {
        for (int j = 0; j < bins; j++) {
            int index = i - j + bins / 2;
            if (index < 0) index = 0;
            if (index >= bins) index = bins - 1;
            smoothed_histogram[i] += histogram[index] * gaussian_kernel[j];
        }
    }

    // Find the highest peak p1
    int p1 = 0;
    for (int i = 1; i < bins; i++) {
        if (smoothed_histogram[i] > smoothed_histogram[p1]) {
            p1 = i;
        }
    }

    // Find the second highest peak p2 at least 5 bins away from p1
    int p2 = -1;
    double max_val = 0.0;
    for (int i = 0; i < bins; i++) {
        if (abs(i - p1) >= 5 && smoothed_histogram[i] > max_val) {
            max_val = smoothed_histogram[i];
            p2 = i;
        }
    }

    // If p2 is not found, set threshold to bin 32 (value 0.5)
    double threshold = 0.5;
    if (p2 != -1) {
        // Find the minimum between p1 and p2
        int start = p1 < p2 ? p1 : p2;
        int end = p1 < p2 ? p2 : p1;
        for (int i = start + 1; i < end; i++) {
            if (smoothed_histogram[i] < smoothed_histogram[start]) {
                start = i;
            }
        }
        threshold = start * bin_width;
    }

    // Binarize the image based on the threshold
    for (int i = 0; i < size; i++) {
        out[i] = in[i] > threshold ? 1.0 : 0.0;
    }
}
