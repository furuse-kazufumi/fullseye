#include <math.h>
#include <stdlib.h>

// Pseudo-random number generator using a simple linear congruential generator (LCG)
// This is used to generate deterministic noise patterns based on the seed derived from 'a'.
static double lcg_random(unsigned int* seed) {
    *seed = (*seed * 1103515245 + 12345) % 4294967296;
    return (double)(*seed) / 4294967296.0;
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the seed based on 'a'
    unsigned int seed = (unsigned int)(a * 997) + 7;
    
    // Calculate the standard deviation based on 'b'
    double stddev = 0.02 + 0.2 * b;
    
    // Iterate over each pixel in the image
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Generate a Gaussian distributed random number using the Box-Muller transform
            double u1 = lcg_random(&seed);
            double u2 = lcg_random(&seed);
            double z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * M_PI * u2);
            
            // Add the noise to the pixel value
            double noisy_value = in[y * w + x] + z0 * stddev;
            
            // Clamp the value to the range [0, 1]
            if (noisy_value < 0.0) noisy_value = 0.0;
            if (noisy_value > 1.0) noisy_value = 1.0;
            
            // Store the result in the output image
            out[y * w + x] = noisy_value;
        }
    }
}
