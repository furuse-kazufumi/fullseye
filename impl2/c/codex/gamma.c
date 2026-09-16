#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x;
    const double gamma = 0.5 + 1.5 * a;

    (void)b;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            const size_t i = (size_t)y * (size_t)w + (size_t)x;
            double v = in[i];

            /*
             * 仕様で未規定の NaN は、比較によるクリップでは変更せず、
             * pow() を通じて通常どおり NaN として伝播させる。
             */
            if (v < 0.0)
                v = 0.0;
            else if (v > 1.0)
                v = 1.0;

            out[i] = pow(v, gamma);
        }
    }
}
