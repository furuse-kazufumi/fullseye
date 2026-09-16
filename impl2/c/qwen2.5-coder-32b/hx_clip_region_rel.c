#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int x0 = w, y0 = h, x1 = 0, y1 = 0;

    // Find the bounding box of the region
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (in[y * w + x] > 0.5) {
                if (x < x0) x0 = x;
                if (y < y0) y0 = y;
                if (x > x1) x1 = x;
                if (y > y1) y1 = y;
            }
        }
    }

    // If the region is empty, return an empty region
    if (x0 > x1 || y0 > y1) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                out[y * w + x] = 0.0;
            }
        }
        return;
    }

    // Calculate the margins to clip
    int my = (int)((y1 - y0) * 0.5 * a);
    int mx = (int)((x1 - x0) * 0.5 * a);

    // Define the clipped region
    int clipped_x0 = x0 + mx;
    int clipped_y0 = y0 + my;
    int clipped_x1 = x1 - mx;
    int clipped_y1 = y1 - my;

    // Clip the region
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (x >= clipped_x0 && x <= clipped_x1 && y >= clipped_y0 && y <= clipped_y1) {
                out[y * w + x] = in[y * w + x];
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
