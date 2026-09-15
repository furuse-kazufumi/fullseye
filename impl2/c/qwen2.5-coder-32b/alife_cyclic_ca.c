#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int N = 3 + (int)(9 * a);
    int steps = 1 + (int)(15 * b);
    int size = h * w;

    // Create a temporary buffer for the next state
    double* next = (double*)malloc(size * sizeof(double));
    if (next == NULL) {
        // Handle memory allocation failure
        memcpy(out, in, size * sizeof(double));
        return;
    }

    // Copy initial state to next
    memcpy(next, in, size * sizeof(double));

    // Function to get the state at a given position with toroidal boundary conditions
    double get_state(const double* img, int y, int x) {
        y = (y + h) % h;
        x = (x + w) % w;
        return img[y * w + x];
    }

    // Perform the cyclic cellular automaton steps
    for (int step = 0; step < steps; step++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                int current_state = (int)(next[idx] * (N - 1));
                int next_state = (current_state + 1) % N;

                // Check Moore neighborhood
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        int ny = y + dy;
                        int nx = x + dx;
                        if ((int)(get_state(next, ny, nx) * (N - 1)) == next_state) {
                            out[idx] = (double)next_state / (N - 1);
                            goto next_pixel;
                        }
                    }
                }
                out[idx] = next[idx];
            next_pixel:;
            }
        }
        // Swap out and next for the next iteration
        double* temp = out;
        out = next;
        next = temp;
    }

    // If the number of steps is even, copy the result back to out
    if (steps % 2 == 0) {
        memcpy(out, next, size * sizeof(double));
    }

    // Free the temporary buffer
    free(next);
}
