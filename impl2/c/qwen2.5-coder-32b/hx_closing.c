#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int radius = 1 + (int)(a * 4);
    int kernel_size = 2 * radius + 1;
    int kernel_area = kernel_size * kernel_size;

    // Allocate temporary buffer for dilation
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        return; // Memory allocation failed
    }

    // Dilation
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            temp[y * w + x] = 0.0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        temp[y * w + x] = fmax(temp[y * w + x], in[ny * w + nx]);
                    }
                }
            }
        }
    }

    // Erosion
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 1.0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        out[y * w + x] = fmin(out[y * w + x], temp[ny * w + nx]);
                    }
                }
            }
        }
    }

    // Free temporary buffer
    free(temp);
}
