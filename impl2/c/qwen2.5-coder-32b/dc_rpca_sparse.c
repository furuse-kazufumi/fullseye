#include <math.h>
#include <stdlib.h>
#include <string.h>

// Helper function to perform soft thresholding
static double soft_threshold(double x, double threshold) {
    if (x > threshold) {
        return x - threshold;
    } else if (x < -threshold) {
        return x + threshold;
    } else {
        return 0.0;
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Parameters for the algorithm
    int m = h;
    int n = w;
    double lambda = (0.5 + 1.5 * a) / sqrt(fmax(m, n));
    double mu = 1.25 / lambda; // Initial value for mu
    double mu_final = mu;
    double epsilon = 1e-7; // Tolerance for convergence
    int max_iter = 1000; // Maximum number of iterations

    // Allocate memory for L, S, and Y
    double* L = (double*)calloc(m * n, sizeof(double));
    double* S = (double*)calloc(m * n, sizeof(double));
    double* Y = (double*)calloc(m * n, sizeof(double));

    // If the image is large, reduce its size
    int reduced_h = (m > 64) ? 64 : m;
    int reduced_w = (n > 64) ? 64 : n;
    double* L_reduced = (double*)calloc(reduced_h * reduced_w, sizeof(double));
    double* S_reduced = (double*)calloc(reduced_h * reduced_w, sizeof(double));
    double* Y_reduced = (double*)calloc(reduced_h * reduced_w, sizeof(double));

    // Downsample the input if necessary
    if (reduced_h != m || reduced_w != n) {
        for (int y = 0; y < reduced_h; y++) {
            for (int x = 0; x < reduced_w; x++) {
                int src_y = (y * m) / reduced_h;
                int src_x = (x * n) / reduced_w;
                L_reduced[y * reduced_w + x] = in[src_y * n + src_x];
                Y_reduced[y * reduced_w + x] = in[src_y * n + src_x];
            }
        }
    } else {
        memcpy(L_reduced, in, m * n * sizeof(double));
        memcpy(Y_reduced, in, m * n * sizeof(double));
    }

    // Perform the inexact ALM for PCP decomposition
    for (int iter = 0; iter < max_iter; iter++) {
        // Update L
        for (int y = 0; y < reduced_h; y++) {
            for (int x = 0; x < reduced_w; x++) {
                double sum = 0.0;
                int count = 0;
                if (y > 0) { sum += L_reduced[(y-1) * reduced_w + x]; count++; }
                if (y < reduced_h - 1) { sum += L_reduced[(y+1) * reduced_w + x]; count++; }
                if (x > 0) { sum += L_reduced[y * reduced_w + (x-1)]; count++; }
                if (x < reduced_w - 1) { sum += L_reduced[y * reduced_w + (x+1)]; count++; }
                L_reduced[y * reduced_w + x] = (sum / count + Y_reduced[y * reduced_w + x] - S_reduced[y * reduced_w + x]) / (1 + 4 / mu);
            }
        }

        // Update S
        for (int y = 0; y < reduced_h; y++) {
            for (int x = 0; x < reduced_w; x++) {
                S_reduced[y * reduced_w + x] = soft_threshold(Y_reduced[y * reduced_w + x] - L_reduced[y * reduced_w + x], lambda / mu);
            }
        }

        // Update Y
        for (int y = 0; y < reduced_h; y++) {
            for (int x = 0; x < reduced_w; x++) {
                Y_reduced[y * reduced_w + x] += mu * (L_reduced[y * reduced_w + x] + S_reduced[y * reduced_w + x] - Y_reduced[y * reduced_w + x]);
            }
        }

        // Check for convergence
        double norm_L = 0.0, norm_S = 0.0, norm_Y = 0.0;
        for (int y = 0; y < reduced_h; y++) {
            for (int x = 0; x < reduced_w; x++) {
                norm_L += L_reduced[y * reduced_w + x] * L_reduced[y * reduced_w + x];
                norm_S += S_reduced[y * reduced_w + x] * S_reduced[y * reduced_w + x];
                norm_Y += Y_reduced[y * reduced_w + x] * Y_reduced[y * reduced_w + x];
            }
        }
        norm_L = sqrt(norm_L);
        norm_S = sqrt(norm_S);
        norm_Y = sqrt(norm_Y);

        if (norm_S < epsilon * (norm_L + norm_Y)) {
            break;
        }

        // Increase mu
        mu *= 1.25;
        mu_final = mu;
    }

    // Upsample L and compute S at the original resolution
    if (reduced_h != m || reduced_w != n) {
        for (int y = 0; y < m; y++) {
            for (int x = 0; x < n; x++) {
                int src_y = (y * reduced_h) / m;
                int src_x = (x * reduced_w) / n;
                L[y * n + x] = L_reduced[src_y * reduced_w + src_x];
            }
        }
        for (int y = 0; y < m; y++) {
            for (int x = 0; x < n; x++) {
                S[y * n + x] = soft_threshold(in[y * n + x] - L[y * n + x], lambda / mu_final);
            }
        }
    } else {
        memcpy(L, L_reduced, m * n * sizeof(double));
        for (int y = 0; y < m; y++) {
            for (int x = 0; x < n; x++) {
                S[y * n + x] = soft_threshold(in[y * n + x] - L[y * n + x], lambda / mu_final);
            }
        }
    }

    // Compute the output as clip(S + 0.5, 0, 1)
    for (int y = 0; y < m; y++) {
        for (int x = 0; x < n; x++) {
            double value = S[y * n + x] + 0.5;
            if (value < 0.0) {
                out[y * n + x] = 0.0;
            } else if (value > 1.0) {
                out[y * n + x] = 1.0;
            } else {
                out[y * n + x] = value;
            }
        }
    }

    // Free allocated memory
    free(L);
    free(S);
    free(Y);
    free(L_reduced);
    free(S_reduced);
    free(Y_reduced);
}
