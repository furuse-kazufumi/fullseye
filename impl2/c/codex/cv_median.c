#include <stdlib.h>
#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t count;
    unsigned char *src;
    int radius, ksize;
    int y, x;

    (void)b;

    /*
     * The specification does not define the exact floating-point-to-uint8
     * conversion rule. This implementation clips to [0,1], rounds to the
     * nearest integer in [0,255], treats NaN as 0, and converts the filtered
     * uint8 result back to double by dividing by 255.
     */
    if (isnan(a) || a < 0.0)
        a = 0.0;
    else if (a > 1.0)
        a = 1.0;

    ksize = 3 + 2 * (int)(a * 3.0);
    radius = ksize / 2;

    count = (size_t)h * (size_t)w;
    src = (unsigned char *)malloc(count * sizeof(*src));

    /*
     * Since the function has no error return, allocation failure is handled
     * deterministically by producing a black image.
     */
    if (src == NULL) {
        size_t i;
        for (i = 0; i < count; ++i)
            out[i] = 0.0;
        return;
    }

    {
        size_t i;
        for (i = 0; i < count; ++i) {
            double v = in[i];

            if (isnan(v) || v <= 0.0)
                src[i] = 0;
            else if (v >= 1.0)
                src[i] = 255;
            else
                src[i] = (unsigned char)floor(v * 255.0 + 0.5);
        }
    }

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            unsigned char values[81];
            int n = 0;
            int dy, dx, i;

            for (dy = -radius; dy <= radius; ++dy) {
                int sy = y + dy;

                if (sy < 0)
                    sy = 0;
                else if (sy >= h)
                    sy = h - 1;

                for (dx = -radius; dx <= radius; ++dx) {
                    int sx = x + dx;
                    unsigned char value;

                    if (sx < 0)
                        sx = 0;
                    else if (sx >= w)
                        sx = w - 1;

                    value = src[(size_t)sy * (size_t)w + (size_t)sx];

                    i = n;
                    while (i > 0 && values[i - 1] > value) {
                        values[i] = values[i - 1];
                        --i;
                    }
                    values[i] = value;
                    ++n;
                }
            }

            out[(size_t)y * (size_t)w + (size_t)x] =
                (double)values[n / 2] / 255.0;
        }
    }

    free(src);
}
