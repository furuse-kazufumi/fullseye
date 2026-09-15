#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    const double Du = 0.16;
    const double Dv = 0.08;
    const double F = 0.02 + 0.06 * a;
    const double K = 0.05 + 0.02 * b;
    const int T = 8 + (int)(20 * a);

    double* u = (double*)malloc(h * w * sizeof(double));
    double* v = (double*)malloc(h * w * sizeof(double));
    double* u_new = (double*)malloc(h * w * sizeof(double));
    double* v_new = (double*)malloc(h * w * sizeof(double));

    // Initialize u and v
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            u[y * w + x] = 1.0 - in[y * w + x];
            v[y * w + x] = in[y * w + x];
        }
    }

    // Laplacian function with toroidal boundary conditions
    double laplacian(const double* field, int x, int y) {
        int left = (x - 1 + w) % w;
        int right = (x + 1) % w;
        int up = (y - 1 + h) % h;
        int down = (y + 1) % h;
        return (field[up * w + x] + field[down * w + x] + field[y * w + left] + field[y * w + right] - 4 * field[y * w + x]);
    }

    // Time integration
    for (int t = 0; t < T; t++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double lap_u = laplacian(u, x, y);
                double lap_v = laplacian(v, x, y);
                u_new[y * w + x] = u[y * w + x] + Du * lap_u - u[y * w + x] * v[y * w + x] * v[y * w + x] + F * (1 - u[y * w + x]);
                v_new[y * w + x] = v[y * w + x] + Dv * lap_v + u[y * w + x] * v[y * w + x] * v[y * w + x] - (F + K) * v[y * w + x];
            }
        }
        memcpy(u, u_new, h * w * sizeof(double));
        memcpy(v, v_new, h * w * sizeof(double));
    }

    // Normalize v field to [0, 1]
    double v_min = v[0];
    double v_max = v[0];
    for (int i = 1; i < h * w; i++) {
        if (v[i] < v_min) v_min = v[i];
        if (v[i] > v_max) v_max = v[i];
    }
    double v_range = v_max - v_min;
    for (int i = 0; i < h * w; i++) {
        out[i] = (v[i] - v_min) / v_range;
    }

    free(u);
    free(v);
    free(u_new);
    free(v_new);
}
