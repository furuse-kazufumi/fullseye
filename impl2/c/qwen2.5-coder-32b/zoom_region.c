#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the zoom scale factor
    double s = 0.7 + 0.6 * a;

    // Calculate the center of the image
    double cx = w / 2.0;
    double cy = h / 2.0;

    // Initialize the output region to 0
    memset(out, 0, h * w * sizeof(double));

    // Iterate over each pixel in the output image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Calculate the corresponding position in the input image
            double ix = (x - cx) / s + cx;
            double iy = (y - cy) / s + cy;

            // Reflect the coordinates if they are outside the image boundaries
            if (ix < 0) ix = -ix;
            if (ix >= w) ix = 2 * w - ix - 1;
            if (iy < 0) iy = -iy;
            if (iy >= h) iy = 2 * h - iy - 1;

            // Get the integer coordinates for interpolation
            int ix0 = (int)ix;
            int iy0 = (int)iy;
            int ix1 = ix0 + 1;
            int iy1 = iy0 + 1;

            // Clamp the coordinates to the image boundaries
            if (ix0 < 0) ix0 = 0;
            if (ix0 >= w) ix0 = w - 1;
            if (ix1 < 0) ix1 = 0;
            if (ix1 >= w) ix1 = w - 1;
            if (iy0 < 0) iy0 = 0;
            if (iy0 >= h) iy0 = h - 1;
            if (iy1 < 0) iy1 = 0;
            if (iy1 >= h) iy1 = h - 1;

            // Perform bilinear interpolation
            double dx = ix - ix0;
            double dy = iy - iy0;
            double v00 = in[iy0 * w + ix0];
            double v01 = in[iy0 * w + ix1];
            double v10 = in[iy1 * w + ix0];
            double v11 = in[iy1 * w + ix1];
            double interpolated_value = (1 - dx) * (1 - dy) * v00 + dx * (1 - dy) * v01 + (1 - dx) * dy * v10 + dx * dy * v11;

            // Rebinarize the interpolated value
            out[y * w + x] = (interpolated_value >= 0.5) ? 1.0 : 0.0;
        }
    }
}
