#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Richardson-Lucy deconvolution assumes a small Gaussian PSF (sigma = RL_SIGMA).
    // 'a' sets the iteration count n = 1 + round(a * 14) (1..15); 'b' is ignored.
    const double RL_SIGMA = 1.0; // Gaussian PSF sigma
    const int max_iterations = 15; // Maximum number of iterations
    int iterations = (int)round(a * max_iterations); // Calculate iterations based on 'a'
    iterations = (iterations < 1) ? 1 : iterations; // Ensure at least 1 iteration

    // Gaussian PSF kernel size
    const int kernel_size = 5;
    double psf[kernel_size * kernel_size];
    double gaussian_psf(double sigma, int size);

    // Initialize PSF
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        psf[i] = 0.0;
    }
    gaussian_psf(RL_SIGMA, kernel_size, psf);

    // Normalize PSF
    double psf_sum = 0.0;
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        psf_sum += psf[i];
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        psf[i] /= psf_sum;
    }

    // Initialize output image
    for (int i = 0; i < h * w; i++) {
        out[i] = in[i];
    }

    // Richardson-Lucy deconvolution
    for (int iter = 0; iter < iterations; iter++) {
        double u[h * w];
        double u_psf[h * w];
        double u_psf_div_in[h * w];
        double u_next[h * w];

        // Convolve u with PSF
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double sum = 0.0;
                for (int ky = -2; ky <= 2; ky++) {
                    for (int kx = -2; kx <= 2; kx++) {
                        int py = y + ky;
                        int px = x + kx;
                        if (py >= 0 && py < h && px >= 0 && px < w) {
                            sum += psf[(ky + 2) * 5 + (kx + 2)] * out[py * w + px];
                        }
                    }
                }
                u[y * w + x] = sum;
            }
        }

        // Compute u * psf / in
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                u_psf[y * w + x] = u[y * w + x];
                u_psf_div_in[y * w + x] = u_psf[y * w + x] / in[y * w + x];
            }
        }

        // Convolve u_psf_div_in with PSF
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double sum = 0.0;
                for (int ky = -2; ky <= 2; ky++) {
                    for (int kx = -2; kx <= 2; kx++) {
                        int py = y + ky;
                        int px = x + kx;
                        if (py >= 0 && py < h && px >= 0 && px < w) {
                            sum += psf[(ky + 2) * 5 + (kx + 2)] * u_psf_div_in[py * w + px];
                        }
                    }
                }
                u_next[y * w + x] = out[y * w + x] * sum;
            }
        }

        // Update output image
        for (int i = 0; i < h * w; i++) {
            out[i] = u_next[i];
        }
    }
}

// Gaussian PSF function
double gaussian_psf(double sigma, int size, double* psf) {
    double sum = 0.0;
    for (int y = -2; y <= 2; y++) {
        for (int x = -2; x <= 2; x++) {
            double g = exp(-(x * x + y * y) / (2 * sigma * sigma));
            psf[(y + 2) * 5 + (x + 2)] = g;
            sum += g;
        }
    }
    return sum;
}
