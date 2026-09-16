#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the radius of the disk based on parameter a
    int radius = (int)(a * 4.0); // a is in [0,1], radius ranges from 0 to 4
    if (radius < 1) radius = 1; // Ensure radius is at least 1

    // Create a mask for the disk structuring element
    int mask_size = 2 * radius + 1;
    int mask[mask_size][mask_size];
    int center = radius;

    for (int i = 0; i < mask_size; i++) {
        for (int j = 0; j < mask_size; j++) {
            int dx = i - center;
            int dy = j - center;
            if (dx * dx + dy * dy <= radius * radius) {
                mask[i][j] = 1;
            } else {
                mask[i][j] = 0;
            }
        }
    }

    // Perform dilation using the disk structuring element
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
            for (int i = -radius; i <= radius; i++) {
                for (int j = -radius; j <= radius; j++) {
                    int ny = y + i;
                    int nx = x + j;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        if (mask[i + radius][j + radius] && in[ny * w + nx] == 1.0) {
                            out[y * w + x] = 1.0;
                            break;
                        }
                    }
                }
                if (out[y * w + x] == 1.0) break;
            }
        }
    }
}
