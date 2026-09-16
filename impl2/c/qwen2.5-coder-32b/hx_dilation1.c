#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int radius = 1 + (int)(a * 4);
    int kernel_size = 2 * radius + 1;
    int kernel_area = kernel_size * kernel_size;

    // Create a circular structuring element
    int* kernel = (int*)malloc(kernel_area * sizeof(int));
    memset(kernel, 0, kernel_area * sizeof(int));

    for (int ky = -radius; ky <= radius; ky++) {
        for (int kx = -radius; kx <= radius; kx++) {
            if (kx * kx + ky * ky <= radius * radius) {
                kernel[(ky + radius) * kernel_size + (kx + radius)] = 1;
            }
        }
    }

    // Perform dilation
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (in[ny * w + nx] == 1.0 && kernel[(ky + radius) * kernel_size + (kx + radius)] == 1) {
                            out[y * w + x] = 1.0;
                            break;
                        }
                    }
                }
                if (out[y * w + x] == 1.0) {
                    break;
                }
            }
        }
    }

    free(kernel);
}
