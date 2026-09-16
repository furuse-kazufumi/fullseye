#include <math.h>
#include <stdlib.h>
#include <string.h>

#define CLAMP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int templateWindowSize = 7;
    int searchWindowSize = 21;
    int hPad = searchWindowSize / 2;
    int wPad = searchWindowSize / 2;
    int hExtended = h + 2 * hPad;
    int wExtended = w + 2 * wPad;
    double h = 3.0 + 20.0 * a;
    double* extendedIn = (double*)malloc(hExtended * wExtended * sizeof(double));
    double* tempOut = (double*)malloc(h * w * sizeof(double));

    // Extend the input image with mirroring
    for (int y = 0; y < hExtended; y++) {
        for (int x = 0; x < wExtended; x++) {
            int srcY = CLAMP(y - hPad, 0, h - 1);
            int srcX = CLAMP(x - wPad, 0, w - 1);
            extendedIn[y * wExtended + x] = in[srcY * w + srcX];
        }
    }

    // Apply Non-Local Means Denoising
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weightSum = 0.0;
            for (int sy = -hPad; sy <= hPad; sy++) {
                for (int sx = -wPad; sx <= wPad; sx++) {
                    double weight = 0.0;
                    for (int ty = -templateWindowSize / 2; ty <= templateWindowSize / 2; ty++) {
                        for (int tx = -templateWindowSize / 2; tx <= templateWindowSize / 2; tx++) {
                            int y1 = y + sy + ty;
                            int x1 = x + sx + tx;
                            int y2 = y + ty;
                            int x2 = x + tx;
                            double diff = extendedIn[y1 * wExtended + x1] - extendedIn[y2 * wExtended + x2];
                            weight += exp(-diff * diff / (h * h));
                        }
                    }
                    sum += extendedIn[(y + sy + hPad) * wExtended + (x + sx + wPad)] * weight;
                    weightSum += weight;
                }
            }
            tempOut[y * w + x] = sum / weightSum;
        }
    }

    // Clamp the output to [0, 1]
    for (int i = 0; i < h * w; i++) {
        out[i] = CLAMP(tempOut[i], 0.0, 1.0);
    }

    free(extendedIn);
    free(tempOut);
}
