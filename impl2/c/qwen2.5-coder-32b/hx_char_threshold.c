#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double sum = 0.0;
    double sum_sq = 0.0;
    int total_pixels = h * w;

    // Calculate mean and standard deviation
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            sum += pixel;
            sum_sq += pixel * pixel;
        }
    }

    double mean = sum / total_pixels;
    double variance = (sum_sq / total_pixels) - (mean * mean);
    double std_dev = sqrt(variance);

    // Calculate threshold
    double k = 0.2 + 1.8 * a;
    double threshold = mean - k * std_dev;

    // Create region based on threshold
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            out[y * w + x] = (pixel < threshold) ? 1.0 : 0.0;
        }
    }
}
