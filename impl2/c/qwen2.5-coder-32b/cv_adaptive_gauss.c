#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int blockSize = 2 * (int)(a * 6) + 3;
    int C = (int)(b * 10);
    int radius = blockSize / 2;

    // Edge handling: replicate the border pixels
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weightSum = 0.0;

            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // Replicate border pixels
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;

                    double weight = exp(-(ky * ky + kx * kx) / (2.0 * radius * radius));
                    sum += in[ny * w + nx] * weight;
                    weightSum += weight;
                }
            }

            double localMean = sum / weightSum;
            out[y * w + x] = (in[y * w + x] > localMean - C) ? 1.0 : 0.0;
        }
    }
}
