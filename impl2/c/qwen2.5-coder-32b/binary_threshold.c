#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int size = h * w;
    int histogram[256] = {0};
    double max_val = 0.0, min_val = 1.0;

    // Calculate the min and max values in the image
    for (int i = 0; i < size; i++) {
        if (in[i] > max_val) max_val = in[i];
        if (in[i] < min_val) min_val = in[i];
    }

    // Normalize the image values to the range [0, 255] for histogram calculation
    for (int i = 0; i < size; i++) {
        int bin = (int)(255.0 * (in[i] - min_val) / (max_val - min_val));
        histogram[bin]++;
    }

    // Otsu's method to find the threshold
    int total = size;
    int sum = 0;
    for (int i = 0; i < 256; i++) {
        sum += i * histogram[i];
    }

    int sumB = 0;
    int wB = 0;
    int wF = 0;
    int max_var = 0;
    int threshold = 0;

    for (int i = 0; i < 256; i++) {
        wB += histogram[i];
        if (wB == 0) continue;
        wF = total - wB;
        if (wF == 0) break;

        sumB += i * histogram[i];
        double mB = (double)sumB / wB;
        double mF = (double)(sum - sumB) / wF;
        int var = wB * wF * (mB - mF) * (mB - mF);

        if (var > max_var) {
            max_var = var;
            threshold = i;
        }
    }

    // Apply the threshold to create the binary image
    double threshold_value = min_val + (threshold / 255.0) * (max_val - min_val);
    for (int i = 0; i < size; i++) {
        out[i] = (in[i] >= threshold_value) ? 1.0 : 0.0;
    }
}
