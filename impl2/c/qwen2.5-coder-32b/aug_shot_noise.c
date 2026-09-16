#include <math.h>
#include <stdlib.h>

// Poisson distribution random number generator using Knuth's algorithm
static unsigned long poisson(double lambda) {
    double L = exp(-lambda);
    unsigned long k = 0;
    double p = 1.0;
    do {
        k++;
        double u = (double)rand() / RAND_MAX;
        p *= u;
    } while (p > L);
    return k - 1;
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the photon scale K
    double K = 5.0 + 250.0 * (1.0 - a);
    // Add a small dark-current pedestal
    double pedestal = 0.05 * b;

    // Seed the random number generator based on a and b
    unsigned int seed = (unsigned int)((a + b) * 10000.0);
    srand(seed);

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Get the input pixel value
            double v = in[y * w + x];
            // Apply the pedestal
            v += pedestal;
            // Scale the value by K
            v *= K;
            // Sample from a Poisson distribution
            unsigned long poisson_value = poisson(v);
            // Scale back the sampled value
            double noisy_value = (double)poisson_value / K;
            // Clamp the value to [0, 1]
            if (noisy_value < 0.0) noisy_value = 0.0;
            if (noisy_value > 1.0) noisy_value = 1.0;
            // Write the noisy value to the output
            out[y * w + x] = noisy_value;
        }
    }
}
