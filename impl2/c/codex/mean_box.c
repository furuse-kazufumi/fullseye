#include <stdlib.h>
#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x, dy, dx;
    int level;
    int size;
    int radius;
    double area;

    (void)b; /* b is unused by specification. */

    /*
     * Knob quantization choice:
     * Divide [0,1] into four equal intervals and map them to 3,5,7,9.
     * The endpoint a == 1 belongs to the final interval.
     */
    level = (int)(a * 4.0);
    if (level < 0)
        level = 0;
    if (level > 3)
        level = 3;

    size = 3 + 2 * level;
    radius = size / 2;
    area = (double)size * (double)size;

    /*
     * Unspecified boundary choice: replicate the nearest edge pixel.
     * Thus every output pixel is averaged over the same size-by-size
     * window, including for 1xN and Nx1 images.
     *
     * Each output value is completed before it is stored. This supports
     * distinct input/output buffers; overlapping buffers are not assumed.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            double sum = 0.0;

            for (dy = -radius; dy <= radius; ++dy) {
                int sy = y + dy;

                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    int sx = x + dx;

                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    sum += in[sy * w + sx];
                }
            }

            out[y * w + x] = sum / area;
        }
    }
}
