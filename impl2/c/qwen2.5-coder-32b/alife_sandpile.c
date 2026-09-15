#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int K = 4 + (int)(12 * a);
    int max_sweeps = 1 + (int)(50 * b);
    int _SANDPILE_BUDGET = 100000; // Budget for grain updates

    int* grains = (int*)malloc(h * w * sizeof(int));
    if (!grains) return; // Memory allocation failed

    // Initialize grains
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            grains[y * w + x] = (int)round(K * in[y * w + x]);
        }
    }

    int budget = _SANDPILE_BUDGET;
    int stable = 0;

    // Relaxation process
    for (int sweep = 0; sweep < max_sweeps && !stable && budget > 0; sweep++) {
        stable = 1;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (grains[y * w + x] >= 4) {
                    stable = 0;
                    grains[y * w + x] -= 4;
                    if (x > 0) grains[y * w + x - 1]++;
                    if (x < w - 1) grains[y * w + x + 1]++;
                    if (y > 0) grains[(y - 1) * w + x]++;
                    if (y < h - 1) grains[(y + 1) * w + x]++;
                    budget -= 4;
                }
            }
        }
    }

    // Find maximum grain height
    int max_height = 0;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (grains[y * w + x] > max_height) {
                max_height = grains[y * w + x];
            }
        }
    }

    // Normalize output
    if (max_height > 0) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                out[y * w + x] = (double)grains[y * w + x] / max_height;
            }
        }
    } else {
        memset(out, 0, h * w * sizeof(double));
    }

    free(grains);
}
