#include <stdlib.h>

void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    const double low_threshold = 0.2 + 0.3 * a;
    const double high_threshold = 0.5 + 0.3 * b;
    size_t n;
    unsigned char *eligible;
    size_t *queue;
    size_t head = 0;
    size_t tail = 0;
    int y, x;

    /*
     * The specification does not define connectivity. This implementation
     * chooses 4-connectivity: pixels connect only through their horizontal
     * and vertical neighbors.
     *
     * "Exceeds a threshold" is interpreted as a strict comparison (>).
     * NaN values consequently belong to neither threshold set.
     */

    if ((size_t)h > (size_t)-1 / (size_t)w) {
        return;
    }
    n = (size_t)h * (size_t)w;

    eligible = (unsigned char *)malloc(n * sizeof(*eligible));
    if (n > (size_t)-1 / sizeof(*queue)) {
        free(eligible);
        for (y = 0; y < h; ++y)
            for (x = 0; x < w; ++x)
                out[(size_t)y * (size_t)w + (size_t)x] = 0.0;
        return;
    }
    queue = (size_t *)malloc(n * sizeof(*queue));

    if (eligible == NULL || queue == NULL) {
        free(eligible);
        free(queue);
        for (y = 0; y < h; ++y)
            for (x = 0; x < w; ++x)
                out[(size_t)y * (size_t)w + (size_t)x] = 0.0;
        return;
    }

    /* Classify before writing out, so in and out may alias safely. */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            size_t i = (size_t)y * (size_t)w + (size_t)x;
            eligible[i] = (unsigned char)(in[i] > low_threshold);
            out[i] = 0.0;
            if (in[i] > high_threshold) {
                out[i] = 1.0;
                queue[tail++] = i;
            }
        }
    }

    while (head < tail) {
        size_t i = queue[head++];
        size_t cy = i / (size_t)w;
        size_t cx = i % (size_t)w;
        size_t j;

        if (cy > 0) {
            j = i - (size_t)w;
            if (eligible[j] && out[j] == 0.0) {
                out[j] = 1.0;
                queue[tail++] = j;
            }
        }
        if (cy + 1 < (size_t)h) {
            j = i + (size_t)w;
            if (eligible[j] && out[j] == 0.0) {
                out[j] = 1.0;
                queue[tail++] = j;
            }
        }
        if (cx > 0) {
            j = i - 1;
            if (eligible[j] && out[j] == 0.0) {
                out[j] = 1.0;
                queue[tail++] = j;
            }
        }
        if (cx + 1 < (size_t)w) {
            j = i + 1;
            if (eligible[j] && out[j] == 0.0) {
                out[j] = 1.0;
                queue[tail++] = j;
            }
        }
    }

    free(queue);
    free(eligible);
}
