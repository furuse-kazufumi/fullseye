#include <math.h>
#include <stdlib.h>
#include <string.h>

#define EPSILON 1e-6

// Cubic B-spline basis function
static double bspline(double t) {
    if (t < 0.0) t = -t;
    if (t < 1.0) return 2.0/3.0 - t*t + 0.5*t*t*t;
    if (t < 2.0) return 4.0/3.0 - t*t + 0.5*t*t*t - 4.0/3.0*t + t*t*t/6.0;
    return 0.0;
}

// Evaluate the displacement at a given point using B-spline interpolation
static void evaluate_displacement(double* phi, int n, double x, double y, double* dx, double* dy) {
    int ix = (int)x;
    int iy = (int)y;
    double wx[4], wy[4];
    *dx = *dy = 0.0;

    for (int i = -1; i <= 2; ++i) {
        wy[i+1] = bspline(y - (iy + i));
        for (int j = -1; j <= 2; ++j) {
            wx[j+1] = bspline(x - (ix + j));
            *dx += wx[j+1] * wy[i+1] * phi[((iy + i) * n + (ix + j)) * 2];
            *dy += wx[j+1] * wy[i+1] * phi[((iy + i) * n + (ix + j)) * 2 + 1];
        }
    }
}

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int n = 2 + (int)(6.0 * b);
    double spacing = 1.0 / (n - 1);
    double amp = 0.45 * a * fmin(h, w);
    double* phi = (double*)malloc(n * n * 2 * sizeof(double));

    // Initialize control lattice
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            double x = j * spacing;
            double y = i * spacing;
            phi[((i * n + j) * 2)] = amp * sin(2.0 * M_PI * y);
            phi[((i * n + j) * 2) + 1] = amp * cos(2.0 * M_PI * x);
        }
    }

    // Apply deformation
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sx = x + 0.5;
            double sy = y + 0.5;
            double dx, dy;
            evaluate_displacement(phi, n, sx * spacing, sy * spacing, &dx, &dy);
            double sx2 = sx - dx;
            double sy2 = sy - dy;

            // Bilinear interpolation
            int x1 = (int)floor(sx2 - 0.5);
            int y1 = (int)floor(sy2 - 0.5);
            int x2 = x1 + 1;
            int y2 = y1 + 1;
            double tx = sx2 - (x1 + 0.5);
            double ty = sy2 - (y1 + 0.5);

            if (x1 < 0) x1 = 0, tx = 0.0;
            if (y1 < 0) y1 = 0, ty = 0.0;
            if (x2 >= w) x2 = w - 1, tx = 1.0;
            if (y2 >= h) y2 = h - 1, ty = 1.0;

            double v11 = in[y1 * w + x1];
            double v12 = in[y1 * w + x2];
            double v21 = in[y2 * w + x1];
            double v22 = in[y2 * w + x2];

            out[y * w + x] = (1.0 - tx) * (1.0 - ty) * v11 +
                             tx * (1.0 - ty) * v12 +
                             (1.0 - tx) * ty * v21 +
                             tx * ty * v22;
        }
    }

    free(phi);
}
