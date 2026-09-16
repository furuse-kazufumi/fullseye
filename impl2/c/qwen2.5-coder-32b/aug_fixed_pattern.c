#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Seed the random number generator with b to ensure the fixed pattern is consistent for the same b
    unsigned int seed = (unsigned int)(b * 1000000);
    srand(seed);

    // Calculate the amplitude for the fixed pattern noise
    double amplitude = 0.02 + 0.2 * a;

    // Generate fixed pattern noise for rows and columns
    double* row_noise = (double*)malloc(h * sizeof(double));
    double* col_noise = (double*)malloc(w * sizeof(double));

    for (int y = 0; y < h; ++y) {
        row_noise[y] = amplitude * (2.0 * ((double)rand() / RAND_MAX) - 1.0);
    }
    for (int x = 0; x < w; ++x) {
        col_noise[x] = amplitude * (2.0 * ((double)rand() / RAND_MAX) - 1.0);
    }

    // Apply the fixed pattern noise to the image
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double noise = 0.67 * col_noise[x] + 0.33 * row_noise[y]; // Column FPN dominates (2/3 weight)
            out[y * w + x] = in[y * w + x] + noise;
            // Clamp the output to the range [0, 1]
            if (out[y * w + x] < 0.0) out[y * w + x] = 0.0;
            if (out[y * w + x] > 1.0) out[y * w + x] = 1.0;
        }
    }

    // Free the allocated memory for row and column noise
    free(row_noise);
    free(col_noise);
}
