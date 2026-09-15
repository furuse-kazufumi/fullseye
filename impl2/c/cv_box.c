#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate kernel size based on parameter a
    int k = 3 + 2 * (int)(a * 3);
    int half_k = k / 2;

    // Edge handling: Use zero-padding
    // This means that pixels near the edge will have fewer neighbors to average over,
    // which is a common approach in image processing.

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // Iterate over the kernel
            for (int ky = -half_k; ky <= half_k; ky++) {
                for (int kx = -half_k; kx <= half_k; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // Check if the neighbor is within bounds
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }

            // Calculate the average
            out[y * w + x] = count > 0 ? sum / count : 0.0;
        }
    }
}
