#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int total_pixels = h * w;
    int histogram[256] = {0};
    double pixel_value;

    // Build histogram
    for (int i = 0; i < total_pixels; i++) {
        pixel_value = in[i] * 255.0;
        if (pixel_value < 0.0) pixel_value = 0.0;
        if (pixel_value > 255.0) pixel_value = 255.0;
        histogram[(int)pixel_value]++;
    }

    // Calculate probabilities and cumulative sums
    double sum = 0.0;
    for (int i = 0; i < 256; i++) {
        sum += i * histogram[i];
    }

    double sumB = 0.0, weightB = 0.0, weightF = 0.0;
    double varMax = 0.0;
    int threshold = 0;

    for (int i = 0; i < 256; i++) {
        weightB += histogram[i];
        if (weightB == 0) continue;

        weightF = total_pixels - weightB;
        if (weightF == 0) break;

        sumB += i * histogram[i];
        double meanB = sumB / weightB;
        double meanF = (sum - sumB) / weightF;

        double varBetween = weightB * weightF * (meanB - meanF) * (meanB - meanF);

        if (varBetween > varMax) {
            varMax = varBetween;
            threshold = i;
        }
    }

    // Apply threshold
    for (int i = 0; i < total_pixels; i++) {
        out[i] = (in[i] * 255.0 > threshold) ? 1.0 : 0.0;
    }
}
