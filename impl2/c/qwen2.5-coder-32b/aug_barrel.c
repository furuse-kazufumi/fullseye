#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double k = 0.6 * a;
    double center_x = w / 2.0;
    double center_y = h / 2.0;
    double max_radius = sqrt(center_x * center_x + center_y * center_y);

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double dx = x - center_x;
            double dy = y - center_y;
            double r = sqrt(dx * dx + dy * dy) / max_radius;

            if (r < 1.0) {
                double r_distorted = r * (1 + k * r * r);
                if (b < 0.5) {
                    r_distorted = r / (1 + k * r * r);
                }
                double theta = atan2(dy, dx);
                double x_distorted = center_x + r_distorted * max_radius * cos(theta);
                double y_distorted = center_y + r_distorted * max_radius * sin(theta);

                int x1 = (int)x_distorted;
                int y1 = (int)y_distorted;
                int x2 = x1 + 1;
                int y2 = y1 + 1;

                if (x1 < 0) x1 = 0;
                if (x1 >= w) x1 = w - 1;
                if (x2 < 0) x2 = 0;
                if (x2 >= w) x2 = w - 1;
                if (y1 < 0) y1 = 0;
                if (y1 >= h) y1 = h - 1;
                if (y2 < 0) y2 = 0;
                if (y2 >= h) y2 = h - 1;

                double wx = x_distorted - x1;
                double wy = y_distorted - y1;

                for (int c = 0; c < 3; ++c) {
                    double q11 = in[y1 * w * 3 + x1 * 3 + c];
                    double q12 = in[y1 * w * 3 + x2 * 3 + c];
                    double q21 = in[y2 * w * 3 + x1 * 3 + c];
                    double q22 = in[y2 * w * 3 + x2 * 3 + c];

                    double v1 = q11 * (1 - wx) + q12 * wx;
                    double v2 = q21 * (1 - wx) + q22 * wx;
                    double v = v1 * (1 - wy) + v2 * wy;

                    out[y * w * 3 + x * 3 + c] = v;
                }
            } else {
                for (int c = 0; c < 3; ++c) {
                    out[y * w * 3 + x * 3 + c] = in[y * w * 3 + x * 3 + c];
                }
            }
        }
    }
}
