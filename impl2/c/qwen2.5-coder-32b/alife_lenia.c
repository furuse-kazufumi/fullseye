#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters derived from 'a'
    double mu = 0.08 + 0.25 * a;
    double sigma = 0.03 + 0.05 * a;
    double dt = 0.10 + 0.15 * a;
    int steps = 1 + (int)(19 * b);

    // Gaussian ring kernel parameters
    double R = 1.0; // Radius of the Gaussian ring
    int kernel_size = (int)(2 * R) + 1;
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;

    // Create Gaussian ring kernel
    for (int ky = -R; ky <= R; ky++) {
        for (int kx = -R; kx <= R; kx++) {
            double r = sqrt(kx * kx + ky * ky);
            if (r > 0 && r <= R) {
                kernel[(ky + R) * kernel_size + (kx + R)] = exp(-(r - 0.5) * (r - 0.5) / (2 * 0.1 * 0.1));
                sum += kernel[(ky + R) * kernel_size + (kx + R)];
            } else {
                kernel[(ky + R) * kernel_size + (kx + R)] = 0.0;
            }
        }
    }

    // Normalize the kernel
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // Temporary storage for intermediate results
    double* u = (double*)malloc(h * w * sizeof(double));
    double* u_new = (double*)malloc(h * w * sizeof(double));
    memcpy(u, in, h * w * sizeof(double));

    // Perform Lenia iterations
    for (int step = 0; step < steps; step++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double U = 0.0;
                for (int ky = -R; ky <= R; ky++) {
                    for (int kx = -R; kx <= R; kx++) {
                        int ny = (y + ky + h) % h; // Periodic boundary condition
                        int nx = (x + kx + w) % w; // Periodic boundary condition
                        U += kernel[(ky + R) * kernel_size + (kx + R)] * u[ny * w + nx];
                    }
                }
                double G_U = 2.0 * exp(-(U - mu) * (U - mu) / (2 * sigma * sigma)) - 1.0;
                u_new[y * w + x] = u[y * w + x] + dt * G_U;
                if (u_new[y * w + x] < 0.0) u_new[y * w + x] = 0.0;
                if (u_new[y * w + x] > 1.0) u_new[y * w + x] = 1.0;
            }
        }
        memcpy(u, u_new, h * w * sizeof(double));
    }

    // Copy the final result to the output
    memcpy(out, u, h * w * sizeof(double));

    // Free allocated memory
    free(kernel);
    free(u);
    free(u_new);
}
