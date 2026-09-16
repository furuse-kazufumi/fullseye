#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Ensure a is within [0, 1]
    a = fmin(1.0, fmax(0.0, a));
    b = fmin(1.0, fmax(0.0, b)); // Ensure b is within [0, 1] but unused

    // Initialize output with zeros
    memset(out, 0, h * w * sizeof(double));

    // Find the largest inscribed circle
    double max_radius = 0.0;
    int center_x = 0, center_y = 0;

    // Distance transform to find the maximum distance to background
    double* distance_transform = (double*)malloc(h * w * sizeof(double));
    if (distance_transform == NULL) {
        return; // Memory allocation failed
    }

    // Compute distance transform
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > 0.5) {
                double min_distance = INFINITY;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = y + dy, nx = x + dx;
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w && in[ny * w + nx] <= 0.5) {
                            double distance = sqrt(dy * dy + dx * dx);
                            min_distance = fmin(min_distance, distance);
                        }
                    }
                }
                distance_transform[y * w + x] = min_distance;
                if (min_distance > max_radius) {
                    max_radius = min_distance;
                    center_x = x;
                    center_y = y;
                }
            }
        }
    }

    free(distance_transform);

    // Calculate the radius of the circle
    double radius = max_radius * (0.6 + 0.8 * a);

    // Draw the circle
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = x - center_x;
            double dy = y - center_y;
            if (dx * dx + dy * dy <= radius * radius) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
