#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double cx = (h - 1) / 2.0;
    double cy = (w - 1) / 2.0;
    double r = 0.42 * fmin(h, w);
    double start = b * 2 * M_PI;
    double sweep = 0.1 + a * (2 * M_PI - 0.1);

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double dx = x - cx;
            double dy = y - cy;
            double dist = sqrt(dx * dx + dy * dy);
            double ang = atan2(dy, dx);

            if (dist <= r) {
                double ang_diff = ang - start;
                if (ang_diff < 0) ang_diff += 2 * M_PI;
                if (ang_diff <= sweep) {
                    out[y * w + x] = 1.0;
                } else {
                    out[y * w + x] = 0.0;
                }
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
