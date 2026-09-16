#include <math.h>
#include <stdlib.h>
#include <string.h>

#define GRID_SIZE 5
#define INTERIOR_SIZE 9
#define BORDER_SIZE 16

static double compute_rbf(double r) {
    return r * r * log(r);
}

static void compute_displacement(double* grid, int h, int w, double a, double b) {
    double amp = 0.15 * a * fmin(h, w);
    double f = 0.5 + 1.5 * b;
    double dx, dy;
    int i, j;

    for (i = 1; i < GRID_SIZE - 1; ++i) {
        for (j = 1; j < GRID_SIZE - 1; ++j) {
            dx = (j - 2.0) / 2.0;
            dy = (i - 2.0) / 2.0;
            grid[(i * GRID_SIZE + j) * 2] = amp * sin(2 * M_PI * f * dx);
            grid[(i * GRID_SIZE + j) * 2 + 1] = amp * cos(2 * M_PI * f * dy);
        }
    }
}

static void compute_weights(double* grid, double* weights) {
    int i, j, k;
    double r, rbf;
    double* K = (double*)malloc(INTERIOR_SIZE * INTERIOR_SIZE * sizeof(double));
    double* P = (double*)malloc(INTERIOR_SIZE * 3 * sizeof(double));
    double* L = (double*)malloc((INTERIOR_SIZE + 3) * (INTERIOR_SIZE + 3) * sizeof(double));
    double* L_inv = (double*)malloc((INTERIOR_SIZE + 3) * (INTERIOR_SIZE + 3) * sizeof(double));
    double* b = (double*)malloc((INTERIOR_SIZE + 3) * sizeof(double));
    double* x = (double*)malloc((INTERIOR_SIZE + 3) * sizeof(double));

    memset(K, 0, INTERIOR_SIZE * INTERIOR_SIZE * sizeof(double));
    memset(P, 0, INTERIOR_SIZE * 3 * sizeof(double));
    memset(L, 0, (INTERIOR_SIZE + 3) * (INTERIOR_SIZE + 3) * sizeof(double));
    memset(b, 0, (INTERIOR_SIZE + 3) * sizeof(double));

    for (i = 0; i < INTERIOR_SIZE; ++i) {
        for (j = 0; j < INTERIOR_SIZE; ++j) {
            if (i == j) continue;
            r = sqrt(pow(grid[i * 2] - grid[j * 2], 2) + pow(grid[i * 2 + 1] - grid[j * 2 + 1], 2));
            rbf = compute_rbf(r);
            K[i * INTERIOR_SIZE + j] = rbf;
        }
        P[i * 3] = 1;
        P[i * 3 + 1] = grid[i * 2];
        P[i * 3 + 2] = grid[i * 2 + 1];
    }

    for (i = 0; i < INTERIOR_SIZE; ++i) {
        for (j = 0; j < INTERIOR_SIZE; ++j) {
            L[i * (INTERIOR_SIZE + 3) + j] = K[i * INTERIOR_SIZE + j];
        }
        for (j = 0; j < 3; ++j) {
            L[i * (INTERIOR_SIZE + 3) + INTERIOR_SIZE + j] = P[i * 3 + j];
            L[(INTERIOR_SIZE + j) * (INTERIOR_SIZE + 3) + i] = P[i * 3 + j];
        }
    }

    for (i = 0; i < 3; ++i) {
        for (j = 0; j < 3; ++j) {
            L[(INTERIOR_SIZE + i) * (INTERIOR_SIZE + 3) + INTERIOR_SIZE + j] = (i == j);
        }
    }

    for (i = 0; i < INTERIOR_SIZE; ++i) {
        b[i] = grid[(i + 10) * 2];
        b[i + INTERIOR_SIZE] = grid[(i + 10) * 2 + 1];
    }

    // Simple LU decomposition and back substitution for solving L * L_inv = I
    for (i = 0; i < INTERIOR_SIZE + 3; ++i) {
        for (j = i; j < INTERIOR_SIZE + 3; ++j) {
            for (k = 0; k < i; ++k) {
                L[i * (INTERIOR_SIZE + 3) + j] -= L[i * (INTERIOR_SIZE + 3) + k] * L[k * (INTERIOR_SIZE + 3) + j];
            }
            if (i == j) {
                if (L[i * (INTERIOR_SIZE + 3) + j] == 0) {
                    free(K);
                    free(P);
                    free(L);
                    free(L_inv);
                    free(b);
                    free(x);
                    return;
                }
                L_inv[i * (INTERIOR_SIZE + 3) + j] = 1.0 / L[i * (INTERIOR_SIZE + 3) + j];
            } else {
                L_inv[j * (INTERIOR_SIZE + 3) + i] = L[i * (INTERIOR_SIZE + 3) + j] * L_inv[i * (INTERIOR_SIZE + 3) + i];
            }
        }
    }

    for (i = INTERIOR_SIZE + 2; i >= 0; --i) {
        x[i] = b[i];
        for (j = i + 1; j < INTERIOR_SIZE + 3; ++j) {
            x[i] -= L[j * (INTERIOR_SIZE + 3) + i] * x[j];
        }
        x[i] *= L_inv[i * (INTERIOR_SIZE + 3) + i];
    }

    memcpy(weights, x, (INTERIOR_SIZE + 3) * sizeof(double));

    free(K);
    free(P);
    free(L);
    free(L_inv);
    free(b);
    free(x);
}

static void apply_tps(double* grid, double* weights, double x, double y, double* result) {
    int i;
    double r, rbf;
    double wx = 0, wy = 0;

    for (i = 0; i < INTERIOR_SIZE; ++i) {
        r = sqrt(pow(grid[i * 2] - x, 2) + pow(grid[i * 2 + 1] - y, 2));
        rbf = compute_rbf(r);
        wx += rbf * weights[i];
        wy += rbf * weights[i + INTERIOR_SIZE];
    }

    for (i = 0; i < 3; ++i) {
        wx += weights[INTERIOR_SIZE + 3 + i] * pow(x, i);
        wy += weights[INTERIOR_SIZE + 6 + i] * pow(y, i);
    }

    result[0] = x + wx;
    result[1] = y + wy;
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int i, j;
    double grid[GRID_SIZE * GRID_SIZE * 2];
    double weights[INTERIOR_SIZE * 2 + 9];
    double x, y, x_out, y_out;
    int x1, y1, x2, y2;
    double dx, dy;
    double v1, v2, v3, v4;

    // Initialize control grid
    for (i = 0; i < GRID_SIZE; ++i) {
        for (j = 0; j < GRID_SIZE; ++j) {
            grid[(i * GRID_SIZE + j) * 2] = (j - 2.0) / 2.0;
            grid[(i * GRID_SIZE + j) * 2 + 1] = (i - 2.0) / 2.0;
        }
    }

    // Compute displacement for interior points
    compute_displacement(grid, h, w, a, b);

    // Compute weights for TPS
    compute_weights(grid, weights);

    // Apply TPS to each pixel
    for (i = 0; i < h; ++i) {
        for (j = 0; j < w; ++j) {
            x = (j - w / 2.0) / (w / 2.0);
            y = (i - h / 2.0) / (h / 2.0);

            apply_tps(grid, weights, x, y, &x_out);
            apply_tps(grid, weights + INTERIOR_SIZE, x, y, &y_out);

            x_out = x_out * (w / 2.0) + (w / 2.0);
            y_out = y_out * (h / 2.0) + (h / 2.0);

            x1 = (int)x_out;
            y1 = (int)y_out;
            x2 = x1 + 1;
            y2 = y1 + 1;

            dx = x_out - x1;
            dy = y_out - y1;

            if (x1 < 0 || x1 >= w || y1 < 0 || y1 >= h) {
                out[i * w + j] = 0;
                continue;
            }

            v1 = (x2 < w && y2 < h) ? in[y2 * w + x2] : 0;
            v2 = (x2 < w) ? in[y1 * w + x2] : 0;
            v3 = (y2 < h) ? in[y2 * w + x1] : 0;
            v4 = in[y1 * w + x1];

            out[i * w + j] = (1 - dx) * (1 - dy) * v4 + dx * (1 - dy) * v2 + (1 - dx) * dy * v3 + dx * dy * v1;
        }
    }
}
