#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate block size based on parameter a
    int block_size = 2 * (int)(a * 6) + 3;
    if (block_size < 3) block_size = 3;
    if (block_size > 15) block_size = 15;

    // Allocate temporary buffer for sorting
    double* buffer = (double*)malloc(block_size * block_size * sizeof(double));
    if (!buffer) return; // Memory allocation failed

    // Process each pixel in the image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int count = 0;
            // Collect pixel values within the block
            for (int by = -block_size / 2; by <= block_size / 2; by++) {
                for (int bx = -block_size / 2; bx <= block_size / 2; bx++) {
                    int ny = y + by;
                    int nx = x + bx;
                    // Handle boundary conditions by clamping
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        buffer[count++] = in[ny * w + nx];
                    }
                }
            }
            // Sort the collected values to find the median
            qsort(buffer, count, sizeof(double), (int (*)(const void*, const void*))strcmp);
            double median = buffer[count / 2];
            // Apply thresholding based on the median
            out[y * w + x] = (in[y * w + x] > median) ? 1.0 : 0.0;
        }
    }

    // Free the temporary buffer
    free(buffer);
}
