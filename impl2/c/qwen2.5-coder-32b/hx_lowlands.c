#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int size = 3 + (int)(a * 6);
    if (size < 3) size = 3;
    if (size > 9) size = 9;

    int half_size = size / 2;
    double* min_filter = (double*)malloc(h * w * sizeof(double));
    if (min_filter == NULL) return;

    // Apply minimum filter with mirror boundary condition
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            for (int dy = -half_size; dy <= half_size; dy++) {
                for (int dx = -half_size; dx <= half_size; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny < 0) ny = -ny - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    if (in[ny * w + nx] < min_val) {
                        min_val = in[ny * w + nx];
                    }
                }
            }
            min_filter[y * w + x] = min_val;
        }
    }

    // Calculate the mean of the image
    double sum = 0.0;
    for (int i = 0; i < h * w; i++) {
        sum += in[i];
    }
    double mean = sum / (h * w);

    // Determine the region
    for (int i = 0; i < h * w; i++) {
        if (in[i] <= min_filter[i] + 1e-6 && in[i] < mean) {
            out[i] = 1.0;
        } else {
            out[i] = 0.0;
        }
    }

    free(min_filter);
}
