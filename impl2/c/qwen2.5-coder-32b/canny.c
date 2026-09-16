#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters for Gaussian blur
    double sigma = 0.5 + 1.5 * a; // Scale sigma between 0.5 and 2.0
    double threshold = 0.1 + 0.5 * b; // Scale threshold between 0.1 and 0.6

    // Gaussian kernel size
    int kernel_size = (int)(6 * sigma) + 1; // Ensure the kernel is large enough
    int half_kernel = kernel_size / 2;

    // Allocate memory for Gaussian kernel
    double* kernel = (double*)malloc(kernel_size * sizeof(double));
    double sum = 0.0;

    // Create Gaussian kernel
    for (int i = 0; i < kernel_size; i++) {
        int x = i - half_kernel;
        kernel[i] = exp(-(x * x) / (2 * sigma * sigma)) / (sqrt(2 * M_PI) * sigma);
        sum += kernel[i];
    }

    // Normalize the kernel
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // Allocate memory for intermediate blurred image
    double* blurred = (double*)malloc(h * w * sizeof(double));

    // Apply Gaussian blur horizontally
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int nx = x + k - half_kernel;
                if (nx < 0) nx = 0; // Clamp to edge
                if (nx >= w) nx = w - 1; // Clamp to edge
                sum += in[y * w + nx] * kernel[k];
            }
            blurred[y * w + x] = sum;
        }
    }

    // Apply Gaussian blur vertically
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int ny = y + k - half_kernel;
                if (ny < 0) ny = 0; // Clamp to edge
                if (ny >= h) ny = h - 1; // Clamp to edge
                sum += blurred[ny * w + x] * kernel[k];
            }
            blurred[y * w + x] = sum;
        }
    }

    // Free the Gaussian kernel
    free(kernel);

    // Sobel operator for edge detection
    const double sobel_x[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    const double sobel_y[3][3] = {
        {-1, -2, -1},
        { 0,  0,  0},
        { 1,  2,  1}
    };

    // Apply Sobel filter
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double grad_x = 0.0, grad_y = 0.0;
            for (int ky = 0; ky < 3; ky++) {
                for (int kx = 0; kx < 3; kx++) {
                    int ny = y + ky - 1;
                    int nx = x + kx - 1;
                    if (ny < 0) ny = 0; // Clamp to edge
                    if (ny >= h) ny = h - 1; // Clamp to edge
                    if (nx < 0) nx = 0; // Clamp to edge
                    if (nx >= w) nx = w - 1; // Clamp to edge
                    grad_x += blurred[ny * w + nx] * sobel_x[ky][kx];
                    grad_y += blurred[ny * w + nx] * sobel_y[ky][kx];
                }
            }
            double gradient_magnitude = sqrt(grad_x * grad_x + grad_y * grad_y);
            out[y * w + x] = (gradient_magnitude > threshold) ? 1.0 : 0.0;
        }
    }

    // Free the intermediate blurred image
    free(blurred);
}
