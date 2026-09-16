#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x, i;
    int steps;
    int dir;
    int k;
    static const int dy[4] = {-1, 0, 1, 0};
    static const int dx[4] = {0, 1, 0, -1};

    /*
     * Choices not fixed explicitly by the specification:
     * - Values >= 0.5 are black (1); values < 0.5 are white (0).
     * - For even dimensions, the starting cell is (h/2, w/2).
     * - b is divided into four equal intervals:
     *   [0,.25)=up, [.25,.5)=right, [.5,.75)=down, [.75,1]=left.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            i = y * w + x;
            out[i] = (in[i] >= 0.5) ? 1.0 : 0.0;
        }
    }

    steps = 1 + (int)(400.0 * a);

    dir = (int)(4.0 * b);
    if (dir < 0)
        dir = 0;
    else if (dir > 3)
        dir = 3;

    y = h / 2;
    x = w / 2;

    for (k = 0; k < steps; ++k) {
        i = y * w + x;

        if (out[i] == 0.0) {
            dir = (dir + 1) & 3;
            out[i] = 1.0;
        } else {
            dir = (dir + 3) & 3;
            out[i] = 0.0;
        }

        y += dy[dir];
        x += dx[dir];

        if (y < 0)
            y = h - 1;
        else if (y >= h)
            y = 0;

        if (x < 0)
            x = w - 1;
        else if (x >= w)
            x = 0;
    }
}
