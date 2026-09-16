void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y;
    int x;

    (void)a;
    (void)b;

    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int i = y * w + x;
            out[i] = (in[i] > 0.5) ? 0.0 : 1.0;
        }
    }
}
