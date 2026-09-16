#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Seed the random number generator based on the parameters a and b
    unsigned int seed = (unsigned int)((a + b) * 10000);
    srand(seed);

    // Calculate sigma based on parameter a
    double sigma = 0.005 + 0.15 * a;

    // Calculate row bias standard deviation based on parameter b and sigma
    double row_bias_sigma = 0.5 * b * sigma;

    // Apply additive Gaussian read noise to each pixel
    for (int y = 0; y < h; ++y) {
        // Generate a row bias for the current row
        double row_bias = row_bias_sigma * ((double)rand() / RAND_MAX * 2.0 - 1.0);

        for (int x = 0; x < w; ++x) {
            // Generate Gaussian noise for the current pixel
            double noise = sigma * ((double)rand() / RAND_MAX * 2.0 - 1.0);

            // Add row bias and noise to the pixel value
            double noisy_value = in[y * w + x] + row_bias + noise;

            // Clamp the output value to the range [0, 1]
            if (noisy_value < 0.0) {
                noisy_value = 0.0;
            } else if (noisy_value > 1.0) {
                noisy_value = 1.0;
            }

            // Store the result in the output array
            out[y * w + x] = noisy_value;
        }
    }
}
