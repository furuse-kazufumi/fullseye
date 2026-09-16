#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters for the bilateral filter
    const int r = 2; // Fixed radius for the neighborhood window
    const double sigma_s = 1.0 + 3.0 * a; // Spatial standard deviation
    const double sigma_r = 0.05 + 0.4 * b; // Range standard deviation

    // Precompute the spatial Gaussian weights
    double spatial_weights[(2 * r + 1) * (2 * r + 1)];
    int idx = 0;
    for (int dy = -r; dy <= r; ++dy) {
        for (int dx = -r; dx <= r; ++dx) {
            double dist = dx * dx + dy * dy;
            spatial_weights[idx++] = exp(-dist / (2 * sigma_s * sigma_s));
        }
    }

    // Process each pixel in the image
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            double weight_sum = 0.0;

            // Iterate over the neighborhood
            for (int dy = -r; dy <= r; ++dy) {
                for (int dx = -r; dx <= r; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // Handle boundary conditions by clamping to the image edges
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;

                    double pixel_value = in[ny * w + nx];
                    double range_diff = pixel_value - in[y * w + x];
                    double range_weight = exp(-range_diff * range_diff / (2 * sigma_r * sigma_r));

                    int weight_idx = (dy + r) * (2 * r + 1) + (dx + r);
                    double weight = spatial_weights[weight_idx] * range_weight;

                    sum += pixel_value * weight;
                    weight_sum += weight;
                }
            }

            // Compute the filtered pixel value
            out[y * w + x] = sum / weight_sum;
        }
    }
}
