#include <stdlib.h>

void fs2_apply(const double *in, int h, int w, double a, double b, double *out)
{
    size_t count = (size_t)h * (size_t)w;
    unsigned char *src;
    int radius = 1 + (int)(a * 4.0);
    int y, x, dy, dx;

    (void)b;

    /*
     * The contract does not specify whether in and out may overlap.
     * This implementation chooses to support overlap by copying the
     * thresholded input before writing any output.
     *
     * Allocation-failure behavior is unspecified; this implementation
     * chooses to return an empty region in that case.
     */
    src = (unsigned char *)malloc(count);
    if (src == NULL) {
        size_t i;
        for (i = 0; i < count; ++i)
            out[i] = 0.0;
        return;
    }

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t i = (size_t)y * (size_t)w + (size_t)x;
            src[i] = (unsigned char)(in[i] > 0.5);
        }
    }

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int found = 0;

            for (dy = -radius; dy <= radius && !found; ++dy) {
                int yy = y + dy;
                int ady = (dy < 0) ? -dy : dy;
                int horizontal = radius - ady;

                if (yy < 0 || yy >= h)
                    continue;

                for (dx = -horizontal; dx <= horizontal; ++dx) {
                    int xx = x + dx;

                    /* Pixels outside the image are treated as zero. */
                    if (xx >= 0 && xx < w &&
                        src[(size_t)yy * (size_t)w + (size_t)xx]) {
                        found = 1;
                        break;
                    }
                }
            }

            out[(size_t)y * (size_t)w + (size_t)x] =
                found ? 1.0 : 0.0;
        }
    }

    free(src);
}
