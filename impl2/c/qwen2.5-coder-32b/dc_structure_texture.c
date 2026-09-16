#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ITERATIONS 120
#define TAU 0.125

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    if (h < 1 || w < 1) {
        return;
    }

    double weight = 0.02 + 0.28 * a;
    double* u = (double*)malloc(h * w * sizeof(double));
    double* px = (double*)malloc(h * w * sizeof(double));
    double* py = (double*)malloc(h * w * sizeof(double));
    double* divp = (double*)malloc(h * w * sizeof(double));

    if (!u || !px || !py || !divp) {
        free(u);
        free(px);
        free(py);
        free(divp);
        return;
    }

    // Initialize u, px, py
    memcpy(u, in, h * w * sizeof(double));
    memset(px, 0, h * w * sizeof(double));
    memset(py, 0, h * w * sizeof(double));

    for (int iter = 0; iter < MAX_ITERATIONS; ++iter) {
        // Compute div(p)
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                int idx = y * w + x;
                double dx = (x < w - 1) ? px[idx] - px[idx + 1] : -px[idx];
                double dy = (y < h - 1) ? py[idx] - py[idx + w] : -py[idx];
                divp[idx] = dx + dy;
            }
        }

        // Update u
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                int idx = y * w + x;
                u[idx] = in[idx] + TAU * divp[idx];
                if (u[idx] < 0) u[idx] = 0;
                if (u[idx] > 1) u[idx] = 1;
            }
        }

        // Update p
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                int idx = y * w + x;
                double gradx = (x < w - 1) ? (u[idx] - u[idx + 1]) : 0;
                double grady = (y < h - 1) ? (u[idx] - u[idx + w]) : 0;
                double norm = sqrt(gradx * gradx + grady * grady);
                if (norm > 1 / weight) {
                    gradx /= norm;
                    grady /= norm;
                }
                if (x < w - 1) {
                    px[idx] = px[idx] + TAU * gradx;
                    px[idx + 1] = px[idx + 1] - TAU * gradx;
                }
                if (y < h - 1) {
                    py[idx] = py[idx] + TAU * grady;
                    py[idx + w] = py[idx + w] - TAU * grady;
                }
            }
        }
    }

    // Copy u to out
    memcpy(out, u, h * w * sizeof(double));

    free(u);
    free(px);
    free(py);
    free(divp);
}
