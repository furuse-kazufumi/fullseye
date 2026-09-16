#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Seed threshold calculation
    double dark_seed_threshold = 0.3 + 0.2 * a;
    double bright_seed_threshold = 0.7 - 0.2 * a;

    // Beta calculation for diffusion
    double beta = 10.0 + 200.0 * b;

    // Initialize seeds
    int* seeds = (int*)calloc(h * w, sizeof(int));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            if (in[idx] < dark_seed_threshold) {
                seeds[idx] = -1; // Dark seed
            } else if (in[idx] > bright_seed_threshold) {
                seeds[idx] = 1; // Bright seed
            }
        }
    }

    // Random walker algorithm
    int* labels = (int*)malloc(h * w * sizeof(int));
    memcpy(labels, seeds, h * w * sizeof(int));

    int changed;
    do {
        changed = 0;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                if (seeds[idx] == 0) {
                    double sum_weights = 0.0;
                    double weighted_sum = 0.0;

                    // Check neighbors
                    int dy[] = {-1, 1, 0, 0};
                    int dx[] = {0, 0, -1, 1};
                    for (int k = 0; k < 4; k++) {
                        int ny = y + dy[k];
                        int nx = x + dx[k];
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            int nidx = ny * w + nx;
                            double weight = exp(-beta * pow(in[idx] - in[nidx], 2));
                            sum_weights += weight;
                            weighted_sum += weight * labels[nidx];
                        }
                    }

                    int new_label = (weighted_sum / sum_weights) > 0.0 ? 1 : -1;
                    if (labels[idx] != new_label) {
                        labels[idx] = new_label;
                        changed = 1;
                    }
                }
            }
        }
    } while (changed);

    // Determine region boundaries
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            out[idx] = 0.0;
            if (labels[idx] != 0) {
                int dy[] = {-1, 1, 0, 0};
                int dx[] = {0, 0, -1, 1};
                for (int k = 0; k < 4; k++) {
                    int ny = y + dy[k];
                    int nx = x + dx[k];
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        int nidx = ny * w + nx;
                        if (labels[idx] != labels[nidx]) {
                            out[idx] = 1.0;
                            break;
                        }
                    }
                }
            }
        }
    }

    // Clean up
    free(seeds);
    free(labels);
}
