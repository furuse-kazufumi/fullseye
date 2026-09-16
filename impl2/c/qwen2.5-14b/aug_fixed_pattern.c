#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Fixed pattern noise (FPN) is applied by adding a static pattern to the input image.
    // The pattern consists of a per-column offset and a per-row offset.
    // The amplitude of the pattern is determined by the parameter 'a'.
    // The seed for the random number generator is set by the parameter 'b'.
    // The column FPN dominates (2/3 weight) as it does in CMOS column-parallel ADCs.

    // Set the amplitude of the pattern
    double amplitude = 0.02 + 0.2 * a;

    // Seed the random number generator with 'b'
    srand((unsigned int)(b * 1000000));

    // Generate the per-column and per-row offsets
    double* column_offsets = (double*)malloc(w * sizeof(double));
    double* row_offsets = (double*)malloc(h * sizeof(double));

    for (int x = 0; x < w; x++) {
        column_offsets[x] = (rand() / (double)RAND_MAX) * 2 * amplitude - amplitude;
    }

    for (int y = 0; y < h; y++) {
        row_offsets[y] = (rand() / (double)RAND_MAX) * 2 * amplitude - amplitude;
    }

    // Apply the fixed pattern noise to the input image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            double value = in[index];
            double noise = (2.0 / 3.0) * column_offsets[x] + (1.0 / 3.0) * row_offsets[y];
            out[index] = value + noise;
        }
    }

    // Ensure the output values are within the range [0, 1]
    for (int i = 0; i < h * w; i++) {
        if (out[i] < 0) {
            out[i] = 0;
        } else if (out[i] > 1) {
            out[i] = 1;
        }
    }

    // Free the allocated memory
    free(column_offsets);
    free(row_offsets);
}
