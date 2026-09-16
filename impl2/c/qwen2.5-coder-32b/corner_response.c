#include <math.h>
#include <stdlib.h>
#include <string.h>

#define CLAMP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters
    double sigma = a * 2.0 + 0.5; // Convert a from [0,1] to [0.5, 2.5]
    double k = 0.04; // Harris constant

    // Gaussian kernel size and sigma
    int kernel_size = (int)(6 * sigma) + 1; // Ensure the kernel is large enough
    int half_kernel = kernel_size / 2;

    // Allocate memory for Gaussian kernel
    double* gaussian_kernel = (double*)malloc(kernel_size * sizeof(double));
    double sum = 0.0;

    // Create Gaussian kernel
    for (int i = -half_kernel; i <= half_kernel; ++i) {
        gaussian_kernel[i + half_kernel] = exp(-(i * i) / (2 * sigma * sigma)) / (sqrt(2 * M_PI) * sigma);
        sum += gaussian_kernel[i + half_kernel];
    }

    // Normalize Gaussian kernel
    for (int i = 0; i < kernel_size; ++i) {
        gaussian_kernel[i] /= sum;
    }

    // Allocate memory for intermediate images
    double* Ix = (double*)calloc(h * w, sizeof(double));
    double* Iy = (double*)calloc(h * w, sizeof(double));
    double* Ix2 = (double*)calloc(h * w, sizeof(double));
    double* Iy2 = (double*)calloc(h * w, sizeof(double));
    double* Ixy = (double*)calloc(h * w, sizeof(double));

    // Sobel operators
    double sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};

    // Compute Ix and Iy using Sobel operators
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double sum_x = 0.0, sum_y = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    sum_x += in[ny * w + nx] * sobel_x[ky + 1][kx + 1];
                    sum_y += in[ny * w + nx] * sobel_y[ky + 1][kx + 1];
                }
            }
            Ix[y * w + x] = sum_x;
            Iy[y * w + x] = sum_y;
        }
    }

    // Compute Ix2, Iy2, Ixy
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Ix2[y * w + x] = Ix[y * w + x] * Ix[y * w + x];
            Iy2[y * w + x] = Iy[y * w + x] * Iy[y * w + x];
            Ixy[y * w + x] = Ix[y * w + x] * Iy[y * w + x];
        }
    }

    // Apply Gaussian filter to Ix2, Iy2, Ixy
    double* Ix2_smooth = (double*)calloc(h * w, sizeof(double));
    double* Iy2_smooth = (double*)calloc(h * w, sizeof(double));
    double* Ixy_smooth = (double*)calloc(h * w, sizeof(double));

    for (int y = half_kernel; y < h - half_kernel; ++y) {
        for (int x = half_kernel; x < w - half_kernel; ++x) {
            double sum_ix2 = 0.0, sum_iy2 = 0.0, sum_ixy = 0.0;
            for (int ky = -half_kernel; ky <= half_kernel; ++ky) {
                for (int kx = -half_kernel; kx <= half_kernel; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    sum_ix2 += Ix2[ny * w + nx] * gaussian_kernel[ky + half_kernel] * gaussian_kernel[kx + half_kernel];
                    sum_iy2 += Iy2[ny * w + nx] * gaussian_kernel[ky + half_kernel] * gaussian_kernel[kx + half_kernel];
                    sum_ixy += Ixy[ny * w + nx] * gaussian_kernel[ky + half_kernel] * gaussian_kernel[kx + half_kernel];
                }
            }
            Ix2_smooth[y * w + x] = sum_ix2;
            Iy2_smooth[y * w + x] = sum_iy2;
            Ixy_smooth[y * w + x] = sum_ixy;
        }
    }

    // Compute corner response
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double det = Ix2_smooth[y * w + x] * Iy2_smooth[y * w + x] - Ixy_smooth[y * w + x] * Ixy_smooth[y * w + x];
            double trace = Ix2_smooth[y * w + x] + Iy2_smooth[y * w + x];
            double response = det - k * trace * trace;
            out[y * w + x] = CLAMP(response, 0.0, 1.0);
        }
    }

    // Free allocated memory
    free(gaussian_kernel);
    free(Ix);
    free(Iy);
    free(Ix2);
    free(Iy2);
    free(Ixy);
    free(Ix2_smooth);
    free(Iy2_smooth);
    free(Ixy_smooth);
}
