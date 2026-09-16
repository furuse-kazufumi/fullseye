#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int radius = 1 + (int)(a * 4);
    int kernel_size = 2 * radius + 1;
    int kernel_area = kernel_size * kernel_size;

    // Initialize output with zeros
    memset(out, 0, h * w * sizeof(double));

    // Iterate over each pixel in the image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] == 1.0) {
                int count = 0;
                // Check the neighborhood within the kernel
                for (int ky = -radius; ky <= radius; ky++) {
                    for (int kx = -radius; kx <= radius; kx++) {
                        int ny = y + ky;
                        int nx = x + kx;
                        // Check if the neighbor is within bounds
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (in[ny * w + nx] == 1.0) {
                                count++;
                            }
                        }
                    }
                }
                // If all neighbors within the kernel are 1, set the output to 1
                if (count == kernel_area) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
