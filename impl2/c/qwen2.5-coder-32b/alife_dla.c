#include <math.h>
#include <stdlib.h>
#include <string.h>

#define CLAMP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int generations = 1 + (int)(11.0 * a);
    double threshold = b;

    // Initialize output image with zeros
    memset(out, 0, sizeof(double) * h * w);

    // Find seed points (bright pixels)
    double max_val = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            max_val = fmax(max_val, in[y * w + x]);
        }
    }
    double seed_threshold = 0.75 * max_val;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] >= seed_threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // Moore neighborhood offsets
    int moore[8][2] = {
        {-1, -1}, {-1, 0}, {-1, 1},
        {0, -1},         {0, 1},
        {1, -1}, {1, 0}, {1, 1}
    };

    // Temporary storage for concentration
    double* concentration = (double*)calloc(h * w, sizeof(double));

    for (int gen = 0; gen < generations; ++gen) {
        // Calculate concentration using Gaussian Green's function
        memset(concentration, 0, sizeof(double) * h * w);
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (out[y * w + x] == 1.0) {
                    for (int dy = -1; dy <= 1; ++dy) {
                        for (int dx = -1; dx <= 1; ++dx) {
                            int ny = CLAMP(y + dy, 0, h - 1);
                            int nx = CLAMP(x + dx, 0, w - 1);
                            concentration[ny * w + nx] += 1.0 / (1.0 + dy * dy + dx * dx);
                        }
                    }
                }
            }
        }

        // Find boundary cells and attach them based on concentration
        double* next_out = (double*)calloc(h * w, sizeof(double));
        memcpy(next_out, out, sizeof(double) * h * w);

        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (out[y * w + x] == 0.0) {
                    int is_boundary = 0;
                    for (int i = 0; i < 8; ++i) {
                        int ny = CLAMP(y + moore[i][0], 0, h - 1);
                        int nx = CLAMP(x + moore[i][1], 0, w - 1);
                        if (out[ny * w + nx] == 1.0) {
                            is_boundary = 1;
                            break;
                        }
                    }
                    if (is_boundary) {
                        next_out[y * w + x] = concentration[y * w + x] >= threshold ? 1.0 : 0.0;
                    }
                }
            }
        }

        // Ensure at least one cell attaches
        double max_concentration = 0.0;
        int max_concentration_x = 0, max_concentration_y = 0;
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (next_out[y * w + x] == 0.0 && concentration[y * w + x] > max_concentration) {
                    max_concentration = concentration[y * w + x];
                    max_concentration_x = x;
                    max_concentration_y = y;
                }
            }
        }
        if (max_concentration > 0.0) {
            next_out[max_concentration_y * w + max_concentration_x] = 1.0;
        }

        // Update output
        memcpy(out, next_out, sizeof(double) * h * w);
        free(next_out);
    }

    free(concentration);
}
