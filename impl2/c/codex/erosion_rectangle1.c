#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x, dy, dx;
    int level;
    int side;
    int radius;

    (void)b; /* b is unused by specification. */

    /*
     * The specification does not define the thresholds for mapping a to
     * {3,5,7,9}. This implementation divides [0,1] into four equal intervals:
     * [0,.25)->3, [.25,.5)->5, [.5,.75)->7, [.75,1]->9.
     */
    level = (int)(a * 4.0);
    if (level < 0)
        level = 0;
    if (level > 3)
        level = 3;
    side = 3 + 2 * level;
    radius = side / 2;

    /*
     * The boundary convention is unspecified. Pixels outside the image are
     * treated as background (0), so a structuring element extending beyond
     * the image cannot fit inside the region.
     *
     * This implementation assumes in and out do not overlap; aliasing is not
     * specified by the contract.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int keep = 1;

            if (y < radius || y >= h - radius ||
                x < radius || x >= w - radius) {
                keep = 0;
            } else {
                for (dy = -radius; dy <= radius && keep; ++dy) {
                    for (dx = -radius; dx <= radius; ++dx) {
                        if (in[(y + dy) * w + (x + dx)] != 1.0) {
                            keep = 0;
                            break;
                        }
                    }
                }
            }

            out[y * w + x] = keep ? 1.0 : 0.0;
        }
    }
}
