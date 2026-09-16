#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the radius based on the parameter a
    double radius = (0.05 + 0.35 * a) * fmin(h, w);
    
    // Calculate the center of the image
    double center_y = (h - 1) / 2.0;
    double center_x = (w - 1) / 2.0;
    
    // Iterate over each pixel in the image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // Calculate the distance from the center
            double distance = sqrt((y - center_y) * (y - center_y) + (x - center_x) * (x - center_x));
            
            // Set the pixel to 1 if it is within the radius, otherwise 0
            if (distance <= radius) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
