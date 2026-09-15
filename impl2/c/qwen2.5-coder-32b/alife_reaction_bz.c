#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int thr = 1 + (int)(3 * a);
    int steps = 1 + (int)(20 * b);
    int size = h * w;

    // Create a temporary buffer to store the next state
    double* next = (double*)malloc(size * sizeof(double));
    if (next == NULL) {
        return; // Memory allocation failed
    }

    // Copy initial state to next
    memcpy(next, in, size * sizeof(double));

    // Define the 8 Moore neighbors
    int dx[] = {-1, -1, -1, 0, 1, 1, 1, 0};
    int dy[] = {-1, 0, 1, 1, 1, 0, -1, -1};

    // Perform the specified number of steps
    for (int step = 0; step < steps; step++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                int excited_neighbors = 0;

                // Count excited neighbors
                for (int i = 0; i < 8; i++) {
                    int nx = (x + dx[i] + w) % w; // Wrap around using modulo
                    int ny = (y + dy[i] + h) % h; // Wrap around using modulo
                    int nidx = ny * w + nx;
                    if (next[nidx] == 1.0) {
                        excited_neighbors++;
                    }
                }

                // Apply Greenberg-Hastings rule
                if (next[idx] == 1.0) {
                    out[idx] = 2.0; // Excited becomes refractory
                } else if (next[idx] == 2.0) {
                    out[idx] = 0.0; // Refractory becomes rest
                } else {
                    if (excited_neighbors >= thr) {
                        out[idx] = 1.0; // Rest becomes excited if threshold is met
                    } else {
                        out[idx] = 0.0; // Rest remains rest
                    }
                }
            }
        }

        // Copy the current state to next for the next iteration
        memcpy(next, out, size * sizeof(double));
    }

    // Free the temporary buffer
    free(next);
}
