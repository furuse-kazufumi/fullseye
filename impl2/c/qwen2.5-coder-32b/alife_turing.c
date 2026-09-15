#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Constants
    const double Da = 0.02;
    const double rho = 1.0;
    const double mu_a = 0.5;
    const double rho0 = 0.01;
    const double Dh_base = 0.15;
    const double Dh_range = 1.05;
    const int T_min = 5;
    const int T_range = 25;

    // Calculate Dh and T based on parameters a and b
    double Dh = Dh_base + Dh_range * a;
    int T = T_min + (int)(T_range * b);

    // Allocate temporary arrays for A and H
    double* A = (double*)malloc(h * w * sizeof(double));
    double* H = (double*)malloc(h * w * sizeof(double));
    double* A_new = (double*)malloc(h * w * sizeof(double));
    double* H_new = (double*)malloc(h * w * sizeof(double));

    // Initialize A with input image and H with a homogeneous level
    memcpy(A, in, h * w * sizeof(double));
    memset(H, 0.5, h * w * sizeof(double));

    // Function to compute the Laplacian with periodic boundary conditions
    void laplacian(const double* field, double* result, double D) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int ym1 = (y - 1 + h) % h;
                int yp1 = (y + 1) % h;
                int xm1 = (x - 1 + w) % w;
                int xp1 = (x + 1) % w;
                result[y * w + x] = D * (
                    field[ym1 * w + x] + field[yp1 * w + x] +
                    field[y * w + xm1] + field[y * w + xp1] -
                    4 * field[y * w + x]
                );
            }
        }
    }

    // Main loop for T steps
    for (int t = 0; t < T; t++) {
        laplacian(A, A_new, Da);
        laplacian(H, H_new, Dh);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double A_val = A[idx];
                double H_val = H[idx];
                double A_new_val = A_new[idx];
                double H_new_val = H_new[idx];

                A[idx] = A_val + A_new_val + rho * A_val * A_val / H_val - mu_a * A_val + rho0;
                H[idx] = H_val + H_new_val + rho * A_val * A_val - mu_h * H_val;
            }
        }
    }

    // Normalize the activator field A to the range [0, 1]
    double A_min = A[0];
    double A_max = A[0];
    for (int i = 1; i < h * w; i++) {
        if (A[i] < A_min) A_min = A[i];
        if (A[i] > A_max) A_max = A[i];
    }

    double A_range = A_max - A_min;
    if (A_range > 0) {
        for (int i = 0; i < h * w; i++) {
            out[i] = (A[i] - A_min) / A_range;
        }
    } else {
        memset(out, 0, h * w * sizeof(double));
    }

    // Free allocated memory
    free(A);
    free(H);
    free(A_new);
    free(H_new);
}
