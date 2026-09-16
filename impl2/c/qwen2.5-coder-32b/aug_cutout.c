#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Copy the input image to the output image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // Calculate the size of the cutout patch
    int patch_size = (int)ceil(a * fmin(h, w));
    if (patch_size < 1) {
        patch_size = 1;
    }

    // Determine the fill value based on the value of b
    double fill_value = (b <= 0.5) ? 0.0 : 0.5;

    // Calculate the top-left corner of the cutout patch
    // Using a deterministic seed based on b to ensure reproducibility
    unsigned int seed = (unsigned int)(b * 1000);
    srand(seed);

    int x_start = rand() % (w - patch_size + 1);
    int y_start = rand() % (h - patch_size + 1);

    // Apply the cutout by filling the patch with the fill value
    for (int y = y_start; y < y_start + patch_size; y++) {
        for (int x = x_start; x < x_start + patch_size; x++) {
            out[y * w + x] = fill_value;
        }
    }
}
