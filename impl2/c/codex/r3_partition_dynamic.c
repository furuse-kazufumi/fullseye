void fs2_apply(const double* in, int h, int w, double a, double b, double* out)
{
    int x, y;
    int max_density = 0;
    int min_positive_density = h + 1;

    (void)b;

    /* Density uniformity is judged only among nonempty columns.
       Empty columns are background and are left unchanged. */
    for (x = 0; x < w; ++x) {
        int density = 0;

        for (y = 0; y < h; ++y) {
            if (in[y * w + x] != 0.0) {
                ++density;
            }
        }

        if (density > max_density) {
            max_density = density;
        }
        if (density > 0 && density < min_positive_density) {
            min_positive_density = density;
        }
    }

    /* An empty region or a region with uniform positive column density
       has no neck columns and is returned unchanged. */
    if (max_density == 0 || min_positive_density == max_density) {
        for (y = 0; y < h; ++y) {
            for (x = 0; x < w; ++x) {
                out[y * w + x] =
                    (in[y * w + x] != 0.0) ? 1.0 : 0.0;
            }
        }
        return;
    }

    for (x = 0; x < w; ++x) {
        int density = 0;
        int remove_column;

        for (y = 0; y < h; ++y) {
            if (in[y * w + x] != 0.0) {
                ++density;
            }
        }

        remove_column =
            (density > 0 && (double)density <= a * (double)max_density);

        for (y = 0; y < h; ++y) {
            out[y * w + x] = remove_column
                ? 0.0
                : ((in[y * w + x] != 0.0) ? 1.0 : 0.0);
        }
    }
}
