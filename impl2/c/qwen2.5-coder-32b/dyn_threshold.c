#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the window size based on parameter a
    int k = (int)(a * 10) + 1; // a is in [0,1], so k ranges from 1 to 11
    int half_k = k / 2;

    // Edge handling: We will use zero-padding for simplicity
    // This means that pixels near the edge will have a smaller window size effectively

    // Temporary storage for the local mean
    double* local_mean = (double*)malloc(h * w * sizeof(double));
    if (local_mean == NULL) {
        return; // Memory allocation failed
    }

    // Calculate local mean using a uniform filter
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int ky = -half_k; ky <= half_k; ky++) {
                for (int kx = -half_k; kx <= half_k; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            local_mean[y * w + x] = sum / count;
        }
    }

    // Calculate the offset
    double offset = (b - 0.5) * 0.4;

    // Apply the dynamic threshold
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double threshold = local_mean[y * w + x] + offset;
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // Free the temporary storage
    free(local_mean);
}
