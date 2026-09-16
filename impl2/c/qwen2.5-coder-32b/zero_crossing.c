#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters
    double sigma = 0.5 + 2 * a; // Gaussian sigma based on parameter a
    int kernel_size = (int)(6 * sigma); // Kernel size for Gaussian filter
    if (kernel_size % 2 == 0) kernel_size++; // Ensure kernel size is odd

    // Allocate memory for Gaussian kernel
    double* kernel = (double*)malloc(kernel_size * sizeof(double));
    double sum = 0.0;

    // Create Gaussian kernel
    for (int i = 0; i < kernel_size; i++) {
        int x = i - kernel_size / 2;
        kernel[i] = exp(-(x * x) / (2 * sigma * sigma)) / (sqrt(2 * M_PI) * sigma);
        sum += kernel[i];
    }

    // Normalize kernel
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // Allocate memory for intermediate image (smoothed image)
    double* smoothed = (double*)malloc(h * w * sizeof(double));

    // Apply Gaussian filter along rows
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double value = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int kx = x + k - kernel_size / 2;
                if (kx < 0) kx = 0; // Boundary handling: clamp to edge
                if (kx >= w) kx = w - 1; // Boundary handling: clamp to edge
                value += in[y * w + kx] * kernel[k];
            }
            smoothed[y * w + x] = value;
        }
    }

    // Apply Gaussian filter along columns
    for (int x = 0; x < w; x++) {
        for (int y = 0; y < h; y++) {
            double value = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int ky = y + k - kernel_size / 2;
                if (ky < 0) ky = 0; // Boundary handling: clamp to edge
                if (ky >= h) ky = h - 1; // Boundary handling: clamp to edge
                value += smoothed[ky * w + x] * kernel[k];
            }
            smoothed[y * w + x] = value;
        }
    }

    // Compute Laplacian of Gaussian (LoG)
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double laplacian = 0.0;

            // Check left and right neighbors
            if (x > 0) laplacian += smoothed[y * w + x - 1];
            if (x < w - 1) laplacian += smoothed[y * w + x + 1];
            laplacian -= 2 * smoothed[y * w + x];

            // Check top and bottom neighbors
            if (y > 0) laplacian += smoothed[(y - 1) * w + x];
            if (y < h - 1) laplacian += smoothed[(y + 1) * w + x];
            laplacian -= 2 * smoothed[y * w + x];

            smoothed[y * w + x] = laplacian;
        }
    }

    // Detect zero crossings
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double center = smoothed[y * w + x];
            int zero_crossing = 0;

            // Check left and right neighbors
            if (x > 0 && center * smoothed[y * w + x - 1] < 0) zero_crossing = 1;
            if (x < w - 1 && center * smoothed[y * w + x + 1] < 0) zero_crossing = 1;

            // Check top and bottom neighbors
            if (y > 0 && center * smoothed[(y - 1) * w + x] < 0) zero_crossing = 1;
            if (y < h - 1 && center * smoothed[(y + 1) * w + x] < 0) zero_crossing = 1;

            out[y * w + x] = zero_crossing ? 1.0 : 0.0;
        }
    }

    // Free allocated memory
    free(kernel);
    free(smoothed);
}
