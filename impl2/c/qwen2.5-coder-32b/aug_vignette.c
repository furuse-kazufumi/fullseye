#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double R = 0.35 + 1.15 * b;
    double center_x = w / 2.0;
    double center_y = h / 2.0;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double dx = x - center_x;
            double dy = y - center_y;
            double r = sqrt(dx * dx + dy * dy) / (0.5 * sqrt(w * w + h * h));
            double falloff = 1.0 / (1.0 + (r / R) * (r / R)) / (1.0 / (1.0 + (1.0 / R) * (1.0 / R)));
            double v = in[y * w + x];
            out[y * w + x] = v * (1.0 - a + a * falloff);
        }
    }
}
