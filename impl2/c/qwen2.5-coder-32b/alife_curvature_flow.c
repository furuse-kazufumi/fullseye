#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int steps = 1 + (int)(29.0 * a);
    double dt = 0.05 + 0.2 * b;
    double eps = 1e-6;

    // Temporary storage for intermediate results
    double* tmp = (double*)malloc(h * w * sizeof(double));
    if (!tmp) return; // Memory allocation failed

    // Copy initial input to output
    memcpy(out, in, h * w * sizeof(double));

    // Periodic boundary condition: wrap around edges
    for (int s = 0; s < steps; ++s) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                int xm1 = (x - 1 + w) % w;
                int xp1 = (x + 1) % w;
                int ym1 = (y - 1 + h) % h;
                int yp1 = (y + 1) % h;

                double u_x = out[yp1 * w + x] - out[ym1 * w + x];
                double u_y = out[y * w + xp1] - out[y * w + xm1];
                double u_xx = out[yp1 * w + x] + out[ym1 * w + x] - 2 * out[y * w + x];
                double u_yy = out[y * w + xp1] + out[y * w + xm1] - 2 * out[y * w + x];
                double u_xy = (out[yp1 * w + xp1] - out[yp1 * w + xm1] - out[ym1 * w + xp1] + out[ym1 * w + xm1]) / 4.0;

                double grad_magnitude = sqrt(u_x * u_x + u_y * u_y + eps);
                double curvature = (u_xx * u_y * u_y - 2 * u_x * u_y * u_xy + u_yy * u_x * u_x) / (grad_magnitude * grad_magnitude + eps);

                tmp[y * w + x] = out[y * w + x] + dt * curvature;
            }
        }
        // Swap tmp and out for the next iteration
        double* swap = tmp;
        tmp = out;
        out = swap;
    }

    // If the number of steps is even, copy the result back to out
    if (steps % 2 == 0) {
        memcpy(out, tmp, h * w * sizeof(double));
    }

    free(tmp);
}
