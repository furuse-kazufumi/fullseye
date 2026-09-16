#include <math.h>
#include <stdlib.h>
#include <string.h>

#define SIGMA_MIN 0.5
#define SIGMA_MAX 2.5

// Gaussian kernel size is fixed to 5x5 for simplicity
#define KERNEL_SIZE 5
#define KERNEL_RADIUS (KERNEL_SIZE / 2)

// Helper function to compute Gaussian kernel
void compute_gaussian_kernel(double* kernel, double sigma) {
    double sum = 0.0;
    for (int y = -KERNEL_RADIUS; y <= KERNEL_RADIUS; ++y) {
        for (int x = -KERNEL_RADIUS; x <= KERNEL_RADIUS; ++x) {
            double r = x * x + y * y;
            kernel[(y + KERNEL_RADIUS) * KERNEL_SIZE + (x + KERNEL_RADIUS)] = exp(-r / (2 * sigma * sigma)) / (2 * M_PI * sigma * sigma);
            sum += kernel[(y + KERNEL_RADIUS) * KERNEL_SIZE + (x + KERNEL_RADIUS)];
        }
    }
    for (int i = 0; i < KERNEL_SIZE * KERNEL_SIZE; ++i) {
        kernel[i] /= sum;
    }
}

// Helper function to apply Gaussian blur
void apply_gaussian_blur(const double* in, double* out, int h, int w, const double* kernel) {
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int ky = -KERNEL_RADIUS; ky <= KERNEL_RADIUS; ++ky) {
                for (int kx = -KERNEL_RADIUS; kx <= KERNEL_RADIUS; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // Clamp to edge for simplicity
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;
                    sum += in[ny * w + nx] * kernel[(ky + KERNEL_RADIUS) * KERNEL_SIZE + (kx + KERNEL_RADIUS)];
                }
            }
            out[y * w + x] = sum;
        }
    }
}

// Helper function to compute gradient magnitude and direction
void compute_gradient(const double* in, double* magnitude, double* direction, int h, int w) {
    static const double sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    static const double sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double grad_x = 0.0, grad_y = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // Clamp to edge for simplicity
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;
                    grad_x += in[ny * w + nx] * sobel_x[ky + 1][kx + 1];
                    grad_y += in[ny * w + nx] * sobel_y[ky + 1][kx + 1];
                }
            }
            magnitude[y * w + x] = sqrt(grad_x * grad_x + grad_y * grad_y);
            direction[y * w + x] = atan2(grad_y, grad_x);
        }
    }
}

// Helper function to perform non-maximum suppression
void non_maximum_suppression(const double* magnitude, const double* direction, double* suppressed, int h, int w) {
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double angle = direction[y * w + x] * 180.0 / M_PI;
            if (angle < 0) angle += 180.0;

            int q = 255, r = 255;

            // angle 0
            if ((angle >= 0 && angle < 22.5) || (angle >= 157.5 && angle <= 180)) {
                q = magnitude[(y + 1) * w + x];
                r = magnitude[(y - 1) * w + x];
            }
            // angle 45
            else if (angle >= 22.5 && angle < 67.5) {
                q = magnitude[(y + 1) * w + (x + 1)];
                r = magnitude[(y - 1) * w + (x - 1)];
            }
            // angle 90
            else if (angle >= 67.5 && angle < 112.5) {
                q = magnitude[y * w + (x + 1)];
                r = magnitude[y * w + (x - 1)];
            }
            // angle 135
            else if (angle >= 112.5 && angle < 157.5) {
                q = magnitude[(y - 1) * w + (x + 1)];
                r = magnitude[(y + 1) * w + (x - 1)];
            }

            if (magnitude[y * w + x] >= q && magnitude[y * w + x] >= r) {
                suppressed[y * w + x] = magnitude[y * w + x];
            } else {
                suppressed[y * w + x] = 0;
            }
        }
    }
}

// Helper function to perform double thresholding and edge tracking
void double_thresholding(const double* suppressed, double* out, int h, int w) {
    double low_threshold = 0.1 * 255;
    double high_threshold = 0.2 * 255;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (suppressed[y * w + x] >= high_threshold) {
                out[y * w + x] = 1.0;
            } else if (suppressed[y * w + x] >= low_threshold) {
                out[y * w + x] = 0.5; // Temporary value for weak edges
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }

    // Edge tracking by hysteresis
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (out[y * w + x] == 0.5) {
                int is_strong = 0;
                for (int ky = -1; ky <= 1; ++ky) {
                    for (int kx = -1; kx <= 1; ++kx) {
                        int ny = y + ky;
                        int nx = x + kx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            if (out[ny * w + nx] == 1.0) {
                                is_strong = 1;
                                break;
                            }
                        }
                    }
                    if (is_strong) break;
                }
                out[y * w + x] = is_strong ? 1.0 : 0.0;
            }
        }
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double sigma = SIGMA_MIN + a * (SIGMA_MAX - SIGMA_MIN);
    double* blurred = (double*)malloc(h * w * sizeof(double));
    double* magnitude = (double*)malloc(h * w * sizeof(double));
    double* direction = (double*)malloc(h * w * sizeof(double));
    double* suppressed = (double*)malloc(h * w * sizeof(double));

    double kernel[KERNEL_SIZE * KERNEL_SIZE];
    compute_gaussian_kernel(kernel, sigma);
    apply_gaussian_blur(in, blurred, h, w, kernel);
    compute_gradient(blurred, magnitude, direction, h, w);
    non_maximum_suppression(magnitude, direction, suppressed, h, w);
    double_thresholding(suppressed, out, h, w);

    free(blurred);
    free(magnitude);
    free(direction);
    free(suppressed);
}
