#include <stdlib.h>
#include <string.h>

// Comparison function for qsort
int compare_doubles(const void* a, const void* b) {
    double arg1 = *(const double*)a;
    double arg2 = *(const double*)b;
    return (arg1 > arg2) - (arg1 < arg2);
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate kernel size based on parameter a
    int kernel_size = 3 + 2 * (int)(a * 3);
    int half_kernel = kernel_size / 2;

    // Allocate temporary buffer for sorting
    double* buffer = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    if (!buffer) return; // Handle memory allocation failure

    // Process each pixel in the image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int buffer_index = 0;

            // Collect pixel values within the kernel
            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // Handle border by replicating edge pixels
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;

                    buffer[buffer_index++] = in[ny * w + nx];
                }
            }

            // Sort the collected pixel values
            qsort(buffer, kernel_size * kernel_size, sizeof(double), compare_doubles);

            // Get the median value
            double median = buffer[(kernel_size * kernel_size) / 2];

            // Assign the median value to the output pixel
            out[y * w + x] = median;
        }
    }

    // Free the temporary buffer
    free(buffer);
}
