#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    size_t n = (size_t)h * (size_t)w;
    size_t *queue;
    size_t head = 0;
    size_t tail = 0;
    int cy = h / 2;
    int cx = w / 2;
    size_t seed_index = (size_t)cy * (size_t)w + (size_t)cx;
    double seed_value = in[seed_index];
    double tolerance = 0.05 + 0.30 * a;
    size_t i;

    (void)b;

    /*
     * The specification does not state the connectivity.  Eight-neighbor
     * connectivity is chosen, matching full connectivity in two dimensions.
     *
     * The specification also does not define allocation-failure behavior.
     * On failure, an empty region is returned.
     *
     * Input and output buffers are assumed not to overlap because aliasing
     * behavior is not specified by the contract.
     */
    for (i = 0; i < n; ++i)
        out[i] = 0.0;

    if (n > ((size_t)-1) / sizeof(*queue))
        return;

    queue = (size_t *)malloc(n * sizeof(*queue));
    if (queue == NULL)
        return;

    out[seed_index] = 1.0;
    queue[tail++] = seed_index;

    while (head < tail) {
        size_t p = queue[head++];
        int y = (int)(p / (size_t)w);
        int x = (int)(p % (size_t)w);
        int dy;
        int dx;

        for (dy = -1; dy <= 1; ++dy) {
            int ny = y + dy;

            if (ny < 0 || ny >= h)
                continue;

            for (dx = -1; dx <= 1; ++dx) {
                int nx;
                size_t q;

                if (dx == 0 && dy == 0)
                    continue;

                nx = x + dx;
                if (nx < 0 || nx >= w)
                    continue;

                q = (size_t)ny * (size_t)w + (size_t)nx;
                if (out[q] != 0.0)
                    continue;

                if (fabs(in[q] - seed_value) <= tolerance) {
                    out[q] = 1.0;
                    queue[tail++] = q;
                }
            }
        }
    }

    free(queue);
}
