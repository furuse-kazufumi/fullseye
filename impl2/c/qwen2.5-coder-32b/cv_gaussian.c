#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate sigma based on parameter a
    double sigmaX = 0.3 + 2.7 * a;
    int kernelSize = (int)(6 * sigmaX + 1); // Kernel size is 6*sigma + 1
    if (kernelSize % 2 == 0) kernelSize++; // Ensure kernel size is odd

    // Allocate memory for the Gaussian kernel
    double* kernel = (double*)malloc(kernelSize * sizeof(double));
    double sum = 0.0;

    // Create the Gaussian kernel
    for (int i = 0; i < kernelSize; i++) {
        int x = i - kernelSize / 2;
        kernel[i] = exp(-(x * x) / (2 * sigmaX * sigmaX)) / (sqrt(2 * M_PI) * sigmaX);
        sum += kernel[i];
    }

    // Normalize the kernel
    for (int i = 0; i < kernelSize; i++) {
        kernel[i] /= sum;
    }

    // Apply the Gaussian filter
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = 0; ky < kernelSize; ky++) {
                int sy = y + ky - kernelSize / 2;
                if (sy < 0) sy = -sy; // Reflect boundary condition
                else if (sy >= h) sy = 2 * h - sy - 2;
                for (int kx = 0; kx < kernelSize; kx++) {
                    int sx = x + kx - kernelSize / 2;
                    if (sx < 0) sx = -sx; // Reflect boundary condition
                    else if (sx >= w) sx = 2 * w - sx - 2;
                    sum += in[sy * w + sx] * kernel[ky] * kernel[kx];
                }
            }
            out[y * w + x] = sum;
        }
    }

    // Free the allocated memory for the kernel
    free(kernel);
}
