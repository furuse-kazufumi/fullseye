#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ITER 60
#define CONVERGENCE_THRESHOLD 1e-7

void svd_decompose(double* A, int m, int n, double* U, double* S, double* Vt) {
    // Simple SVD decomposition using Jacobi method for demonstration purposes.
    // In practice, a more efficient method like LAPACK's dgesvd should be used.
    int p, q, i, j, k;
    double c, s, t, tau, theta, t1, t2, cs, sn;
    double* R = (double*)malloc(m * n * sizeof(double));
    double* R_new = (double*)malloc(m * n * sizeof(double));
    memcpy(R, A, m * n * sizeof(double));

    for (k = 0; k < 100; k++) {
        for (p = 0; p < m; p++) {
            for (q = p + 1; q < n; q++) {
                theta = 0.5 * atan2(2 * R[p * n + q], R[p * n + p] - R[q * n + q]);
                c = cos(theta);
                s = sin(theta);
                for (i = 0; i < m; i++) {
                    t1 = R[i * n + p];
                    t2 = R[i * n + q];
                    R_new[i * n + p] = c * t1 - s * t2;
                    R_new[i * n + q] = s * t1 + c * t2;
                }
                for (j = 0; j < n; j++) {
                    t1 = R[p * n + j];
                    t2 = R[q * n + j];
                    R_new[p * n + j] = c * t1 - s * t2;
                    R_new[q * n + j] = s * t1 + c * t2;
                }
                memcpy(R, R_new, m * n * sizeof(double));
            }
        }
    }

    // Extract U, S, Vt from R
    for (i = 0; i < m; i++) {
        for (j = 0; j < n; j++) {
            if (i == j) {
                S[i] = R[i * n + j];
                R[i * n + j] = 1;
            } else {
                R[i * n + j] = 0;
            }
        }
    }
    memcpy(U, R, m * n * sizeof(double));
    memcpy(Vt, R, m * n * sizeof(double));

    free(R);
    free(R_new);
}

void shrinkage(double* A, int m, int n, double tau) {
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            double val = A[i * n + j];
            A[i * n + j] = (fabs(val) > tau) ? (val > 0 ? val - tau : val + tau) : 0;
        }
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    if (h == 0 || w == 0) {
        return;
    }

    int m = h, n = w;
    if (m > 64 || n > 64) {
        // Resize to 64x64 for processing
        int new_h = 64, new_w = 64;
        double* resized_in = (double*)malloc(new_h * new_w * sizeof(double));
        for (int y = 0; y < new_h; y++) {
            for (int x = 0; x < new_w; x++) {
                int src_y = (y * m) / new_h;
                int src_x = (x * n) / new_w;
                resized_in[y * new_w + x] = in[src_y * n + src_x];
            }
        }
        m = new_h;
        n = new_w;
        in = resized_in;
    }

    double* L = (double*)calloc(m * n, sizeof(double));
    double* S = (double*)calloc(m * n, sizeof(double));
    double* Y = (double*)calloc(m * n, sizeof(double));
    double* U = (double*)malloc(m * n * sizeof(double));
    double* S_diag = (double*)malloc(m * n * sizeof(double));
    double* Vt = (double*)malloc(m * n * sizeof(double));

    double lambda = (0.5 + 1.5 * a) / sqrt(fmax(m, n));
    double mu = 1.0 / lambda;
    double norm_M = 0.0;

    for (int i = 0; i < m * n; i++) {
        norm_M += in[i] * in[i];
    }
    norm_M = sqrt(norm_M);

    for (int iter = 0; iter < MAX_ITER; iter++) {
        // Update L
        for (int i = 0; i < m * n; i++) {
            Y[i] = in[i] - S[i] + (1.0 / mu) * L[i];
        }
        svd_decompose(Y, m, n, U, S_diag, Vt);
        for (int i = 0; i < m * n; i++) {
            if (i < m && i < n) {
                S_diag[i] = fmax(0.0, S_diag[i] - 1.0 / mu);
            } else {
                S_diag[i] = 0.0;
            }
        }
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                L[i * n + j] = 0.0;
                for (int k = 0; k < fmin(m, n); k++) {
                    L[i * n + j] += U[i * n + k] * S_diag[k * n + k] * Vt[k * n + j];
                }
            }
        }

        // Update S
        for (int i = 0; i < m * n; i++) {
            Y[i] = in[i] - L[i] + (1.0 / mu) * S[i];
        }
        shrinkage(Y, m, n, lambda / mu);
        memcpy(S, Y, m * n * sizeof(double));

        // Check convergence
        double norm_diff = 0.0;
        for (int i = 0; i < m * n; i++) {
            double diff = in[i] - L[i] - S[i];
            norm_diff += diff * diff;
        }
        norm_diff = sqrt(norm_diff);
        if (norm_diff <= CONVERGENCE_THRESHOLD * norm_M) {
            break;
        }
    }

    if (m != h || n != w) {
        // Resize L back to original size using bilinear interpolation
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double src_y = (y * m) / (double)h;
                double src_x = (x * n) / (double)w;
                int y1 = (int)src_y;
                int x1 = (int)src_x;
                int y2 = fmin(y1 + 1, m - 1);
                int x2 = fmin(x1 + 1, n - 1);
                double dy = src_y - y1;
                double dx = src_x - x1;
                double val = (1 - dy) * (1 - dx) * L[y1 * n + x1] +
                             (1 - dy) * dx * L[y1 * n + x2] +
                             dy * (1 - dx) * L[y2 * n + x1] +
                             dy * dx * L[y2 * n + x2];
                out[y * w + x] = fmax(0.0, fmin(1.0, val));
            }
        }
    } else {
        for (int i = 0; i < m * n; i++) {
            out[i] = fmax(0.0, fmin(1.0, L[i]));
        }
    }

    free(L);
    free(S);
    free(Y);
    free(U);
    free(S_diag);
    free(Vt);
    if (m != h || n != w) {
        free((void*)in);
    }
}
