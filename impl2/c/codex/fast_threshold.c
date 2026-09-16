void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int y, x;
    const double upper = a + 0.5 + 0.5 * b;

    /*
     * The specification writes the band as (a, upper), so both endpoints
     * are treated as excluded. Values outside [0,1] are compared unchanged.
     * NaN values fail the comparisons and therefore become background.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            const int i = y * w + x;
            const double v = in[i];
            out[i] = (v > a && v < upper) ? 1.0 : 0.0;
        }
    }
}
