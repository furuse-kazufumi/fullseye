#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the streak length L
    int L = 3 + (int)(20 * a);
    if (L % 2 == 0) L++; // Ensure L is odd
    if (L > h && L > w) L = (h > w) ? h : w; // Clamp L to the image dimensions

    // Calculate the angle in radians
    double angle = b * M_PI;

    // Calculate the kernel offsets
    int half_L = L / 2;
    double dx = cos(angle);
    double dy = sin(angle);

    // Reflect border handling
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int i = -half_L; i <= half_L; i++) {
                int px = x + (int)(i * dx);
                int py = y + (int)(i * dy);

                // Reflective border handling
                if (px < 0) px = -px - 1;
                if (px >= w) px = 2 * w - px - 1;
                if (py < 0) py = -py - 1;
                if (py >= h) py = 2 * h - py - 1;

                sum += in[py * w + px];
            }
            out[y * w + x] = sum / L;
        }
    }
}
