#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Define constants
    const double sigma = fmax(2.0, fmin(h, w) / 6.0);
    const double threshold = 0.005 + 0.145 * a;
    const int iterations = (int)round(3 * b);
    const int kernel_size = 3;
    const int padding = kernel_size / 2;

    // Allocate memory for Gaussian filter
    double* gaussian_filter = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -padding; i <= padding; ++i) {
        for (int j = -padding; j <= padding; ++j) {
            double coefficient = exp(-(i * i + j * j) / (2 * sigma * sigma));
            gaussian_filter[(i + padding) * kernel_size + (j + padding)] = coefficient;
            sum += coefficient;
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; ++i) {
        gaussian_filter[i] /= sum;
    }

    // Apply Gaussian filter
    double* filtered_image = (double*)malloc((h + 2 * padding) * (w + 2 * padding) * sizeof(double));
    memset(filtered_image, 0, (h + 2 * padding) * (w + 2 * padding) * sizeof(double));
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int i = -padding; i <= padding; ++i) {
                for (int j = -padding; j <= padding; ++j) {
                    sum += in[y * w + x] * gaussian_filter[(i + padding) * kernel_size + (j + padding)];
                }
            }
            filtered_image[(y + padding) * (w + 2 * padding) + (x + padding)] = sum;
        }
    }

    // Compute deviation
    double* deviation = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            deviation[y * w + x] = fabs(in[y * w + x] - filtered_image[(y + padding) * (w + 2 * padding) + (x + padding)]);
        }
    }

    // Thresholding
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = (deviation[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // Morphological operations
    for (int i = 0; i < iterations; ++i) {
        // Binary opening
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double sum = 0.0;
                for (int i = -1; i <= 1; ++i) {
                    for (int j = -1; j <= 1; ++j) {
                        if (out[(y + i) * w + (x + j)] == 1.0) {
                            sum += 1.0;
                        }
                    }
                }
                out[y * w + x] = (sum > 0) ? 1.0 : 0.0;
            }
        }

        // Binary closing
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double sum = 0.0;
                for (int i = -1; i <= 1; ++i) {
                    for (int j = -1; j <= 1; ++j) {
                        if (out[(y + i) * w + (x + j)] == 1.0) {
                            sum += 1.0;
                        }
                    }
                }
                out[y * w + x] = (sum > 1) ? 1.0 : 0.0;
            }
        }
    }

    // Free allocated memory
    free(gaussian_filter);
    free(filtered_image);
    free(deviation);
}
