#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Initialize output to 0
    memset(out, 0, h * w * sizeof(double));

    // Convert a and b to actual rotation angle and shear factor
    double angle = (a - 0.5) * 40.0 * M_PI / 180.0; // a ranges from -20° to +20°
    double shear = (b - 0.5) * 2.0; // b ranges from -1 to +1

    // Precompute trigonometric values
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);

    // Iterate over each pixel in the output image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Apply inverse affine transformation to find corresponding input pixel
            double x_in = (x - w / 2.0) * cos_theta + (y - h / 2.0) * sin_theta + (y - h / 2.0) * shear;
            double y_in = -(x - w / 2.0) * sin_theta + (y - h / 2.0) * cos_theta;

            // Translate back to image coordinates
            x_in += w / 2.0;
            y_in += h / 2.0;

            // Check if the transformed coordinates are within the input image bounds
            if (x_in >= 0 && x_in < w - 1 && y_in >= 0 && y_in < h - 1) {
                // Bilinear interpolation to determine if the pixel is part of the region
                int x0 = (int)x_in;
                int y0 = (int)y_in;
                int x1 = x0 + 1;
                int y1 = y0 + 1;

                double dx = x_in - x0;
                double dy = y_in - y0;

                double value = (1 - dx) * (1 - dy) * in[y0 * w + x0] +
                               dx * (1 - dy) * in[y0 * w + x1] +
                               (1 - dx) * dy * in[y1 * w + x0] +
                               dx * dy * in[y1 * w + x1];

                // Binarize the interpolated value
                if (value >= 0.5) {
                    out[y * w + x] = 1.0;
                }
            }
        }
    }
}
