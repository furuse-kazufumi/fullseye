#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a sets the peak shift 0.25*W*a px (the shear is centred so the middle row is unmoved)
    // b sets the pan direction (b < 0.5 -> shift right with increasing row, otherwise left)
    double peak_shift = 0.25 * w * a;
    double direction = (b < 0.5) ? 1.0 : -1.0;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Calculate the shift for the current row
            double shift = direction * peak_shift * (2.0 * (y + 0.5) / h - 1.0);
            double src_x = x + shift;

            // Reflecting borders
            if (src_x < 0) {
                src_x = -src_x - 1;
            }
            if (src_x >= w) {
                src_x = 2 * w - src_x - 1;
            }

            // Bilinear interpolation
            int x0 = (int)src_x;
            int x1 = x0 + 1;
            double t = src_x - x0;

            if (x1 >= w) {
                x1 = w - 1;
                t = 1.0;
            }

            double top_left = in[y * w + x0];
            double top_right = in[y * w + x1];
            double interpolated_value = (1.0 - t) * top_left + t * top_right;

            out[y * w + x] = interpolated_value;
        }
    }
}
