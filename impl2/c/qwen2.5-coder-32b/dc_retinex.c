#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Gaussian filter parameters
    double sigma = a * 10.0 + 1.0; // a controls the Gaussian scale, mapping [0,1] to [1,11]
    int kernel_size = (int)(6 * sigma) + 1; // Kernel size is 6*sigma + 1 to cover 3 standard deviations
    int half_kernel = kernel_size / 2;

    // Allocate memory for the Gaussian kernel
    double* kernel = (double*)malloc(kernel_size * sizeof(double));
    double sum = 0.0;

    // Create the Gaussian kernel
    for (int i = -half_kernel; i <= half_kernel; ++i) {
        kernel[i + half_kernel] = exp(-(i * i) / (2 * sigma * sigma));
        sum += kernel[i + half_kernel];
    }

    // Normalize the kernel
    for (int i = 0; i < kernel_size; ++i) {
        kernel[i] /= sum;
    }

    // Allocate memory for the blurred image
    double* blurred = (double*)malloc(h * w * sizeof(double));

    // Apply the Gaussian filter row-wise
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int kx = -half_kernel; kx <= half_kernel; ++kx) {
                int nx = x + kx;
                if (nx < 0) nx = 0; // Reflective boundary condition
                if (nx >= w) nx = w - 1; // Reflective boundary condition
                sum += in[y * w + nx] * kernel[kx + half_kernel];
            }
            blurred[y * w + x] = sum;
        }
    }

    // Apply the Gaussian filter column-wise
    for (int x = 0; x < w; ++x) {
        for (int y = 0; y < h; ++y) {
            double sum = 0.0;
            for (int ky = -half_kernel; ky <= half_kernel; ++ky) {
                int ny = y + ky;
                if (ny < 0) ny = 0; // Reflective boundary condition
                if (ny >= h) ny = h - 1; // Reflective boundary condition
                sum += blurred[ny * w + x] * kernel[ky + half_kernel];
            }
            blurred[y * w + x] = sum;
        }
    }

    // Compute the Retinex reflectance
    double mid_gray = 0.5; // Mid-gray level for fixed log-domain gain
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double log_input = log(in[y * w + x] + 1e-6); // Add small epsilon to avoid log(0)
            double log_blurred = log(blurred[y * w + x] + 1e-6); // Add small epsilon to avoid log(0)
            double retinex = log_input - log_blurred;
            out[y * w + x] = b * (retinex - log(mid_gray)) + mid_gray; // Apply fixed log-domain gain
        }
    }

    // Free allocated memory
    free(kernel);
    free(blurred);
}
