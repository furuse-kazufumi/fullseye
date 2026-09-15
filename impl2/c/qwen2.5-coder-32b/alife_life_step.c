#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Define the rules based on the value of 'a'
    int B3 = (a < 0.333) ? 1 : (a < 0.666) ? 3 : 6;
    int B6 = (a < 0.333) ? 6 : (a < 0.666) ? 3 : 1;
    int S2 = (a < 0.333) ? 2 : (a < 0.666) ? 3 : 4;
    int S3 = (a < 0.333) ? 3 : (a < 0.666) ? 2 : 3;
    int S4 = (a < 0.333) ? 4 : (a < 0.666) ? 3 : 2;
    int S6 = (a < 0.333) ? 6 : (a < 0.666) ? 3 : 1;
    int S7 = (a < 0.333) ? 7 : (a < 0.666) ? 3 : 6;
    int S8 = (a < 0.333) ? 8 : (a < 0.666) ? 3 : 7;

    // Determine the number of generations
    int generations = 1 + (int)(9 * b);

    // Allocate temporary storage for the next generation
    double* next = (double*)malloc(h * w * sizeof(double));
    if (!next) return; // Handle memory allocation failure

    // Initialize the live/dead lattice
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = (in[y * w + x] >= 0.5) ? 1.0 : 0.0;
        }
    }

    // Apply the cellular automaton rules for the specified number of generations
    for (int gen = 0; gen < generations; gen++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int live_neighbors = 0;

                // Count live neighbors with toroidal boundary conditions
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        int ny = (y + dy + h) % h;
                        int nx = (x + dx + w) % w;
                        live_neighbors += (out[ny * w + nx] > 0.5) ? 1 : 0;
                    }
                }

                // Apply the rules
                if (out[y * w + x] > 0.5) {
                    // Live cell
                    next[y * w + x] = (live_neighbors == S2 || live_neighbors == S3 || live_neighbors == S4 || live_neighbors == S6 || live_neighbors == S7 || live_neighbors == S8) ? 1.0 : 0.0;
                } else {
                    // Dead cell
                    next[y * w + x] = (live_neighbors == B3 || live_neighbors == B6) ? 1.0 : 0.0;
                }
            }
        }

        // Swap the current and next generation
        memcpy(out, next, h * w * sizeof(double));
    }

    // Free the temporary storage
    free(next);
}
