#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Initialize output to 0
    memset(out, 0, h * w * sizeof(double));

    // Calculate the gradient magnitude using Sobel operator
    double* gmag = (double*)malloc(h * w * sizeof(double));
    if (gmag == NULL) return;

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double gx = 0.0, gy = 0.0;

            // Calculate gx and gy using Sobel operator
            if (x > 0 && x < w - 1 && y > 0 && y < h - 1) {
                gx = -in[(y-1)*(w) + (x-1)] + in[(y-1)*(w) + (x+1)] -
                     2*in[y*(w) + (x-1)] + 2*in[y*(w) + (x+1)] -
                     in[(y+1)*(w) + (x-1)] + in[(y+1)*(w) + (x+1)];
                gy = -in[(y-1)*(w) + (x-1)] - 2*in[(y-1)*(w) + (x)] - in[(y-1)*(w) + (x+1)] +
                     in[(y+1)*(w) + (x-1)] + 2*in[(y+1)*(w) + (x)] + in[(y+1)*(w) + (x+1)];
            }

            gmag[y * w + x] = sqrt(gx * gx + gy * gy);
        }
    }

    // Find the maximum gradient magnitude
    double max_gmag = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (gmag[i] > max_gmag) {
            max_gmag = gmag[i];
        }
    }

    // Determine the threshold for flat regions
    double threshold = (0.01 + 0.1 * a) * max_gmag;

    // Identify flat regions and label connected components
    int* labels = (int*)malloc(h * w * sizeof(int));
    if (labels == NULL) {
        free(gmag);
        return;
    }
    memset(labels, 0, h * w * sizeof(int));

    int label_count = 0;
    int* label_sizes = (int*)malloc(h * w * sizeof(int));
    if (label_sizes == NULL) {
        free(gmag);
        free(labels);
        return;
    }
    memset(label_sizes, 0, h * w * sizeof(int));

    int* label_sums_x = (int*)malloc(h * w * sizeof(int));
    if (label_sums_x == NULL) {
        free(gmag);
        free(labels);
        free(label_sizes);
        return;
    }
    memset(label_sums_x, 0, h * w * sizeof(int));

    int* label_sums_y = (int*)malloc(h * w * sizeof(int));
    if (label_sums_y == NULL) {
        free(gmag);
        free(labels);
        free(label_sizes);
        free(label_sums_x);
        return;
    }
    memset(label_sums_y, 0, h * w * sizeof(int));

    int dx[] = {-1, -1, -1, 0, 1, 1, 1, 0};
    int dy[] = {-1, 0, 1, 1, 1, 0, -1, -1};

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (gmag[y * w + x] < threshold) {
                int label = 0;
                for (int d = 0; d < 8; d++) {
                    int nx = x + dx[d];
                    int ny = y + dy[d];
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h && labels[ny * w + nx] > 0) {
                        label = labels[ny * w + nx];
                        break;
                    }
                }

                if (label == 0) {
                    label = ++label_count;
                } else {
                    // Merge labels if necessary
                    for (int d = 0; d < 8; d++) {
                        int nx = x + dx[d];
                        int ny = y + dy[d];
                        if (nx >= 0 && nx < w && ny >= 0 && ny < h && labels[ny * w + nx] > 0 && labels[ny * w + nx] != label) {
                            int old_label = labels[ny * w + nx];
                            for (int i = 0; i < h * w; i++) {
                                if (labels[i] == old_label) {
                                    labels[i] = label;
                                }
                            }
                            label_sizes[label] += label_sizes[old_label];
                            label_sums_x[label] += label_sums_x[old_label];
                            label_sums_y[label] += label_sums_y[old_label];
                            label_sizes[old_label] = 0;
                            label_sums_x[old_label] = 0;
                            label_sums_y[old_label] = 0;
                        }
                    }
                }

                labels[y * w + x] = label;
                label_sizes[label]++;
                label_sums_x[label] += x;
                label_sums_y[label] += y;
            }
        }
    }

    // Calculate the center of mass for each component
    for (int label = 1; label <= label_count; label++) {
        if (label_sizes[label] > 0) {
            int cx = (int)round((double)label_sums_x[label] / label_sizes[label]);
            int cy = (int)round((double)label_sums_y[label] / label_sizes[label]);
            if (cx >= 0 && cx < w && cy >= 0 && cy < h) {
                out[cy * w + cx] = 1.0;
            }
        }
    }

    // Free allocated memory
    free(gmag);
    free(labels);
    free(label_sizes);
    free(label_sums_x);
    free(label_sums_y);
}
