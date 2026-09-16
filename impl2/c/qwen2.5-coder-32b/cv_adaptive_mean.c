#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int blockSize = 2 * (int)(a * 6) + 3;
    int C = (int)(b * 10);

    // Edge handling: Use zero-padding for simplicity
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;

            // Calculate the local mean with zero-padding
            for (int ky = -blockSize / 2; ky <= blockSize / 2; ky++) {
                for (int kx = -blockSize / 2; kx <= blockSize / 2; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }

            double localMean = count > 0 ? sum / count : 0.0;
            double threshold = localMean - C;

            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }
}
