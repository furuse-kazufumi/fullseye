void fs2_apply(const double* in, int h, int w,
               double a, double b, double* out)
{
    int y, x;

    (void)a;
    (void)b;

    /*
     * The specification does not define the erosion neighborhood or image-edge
     * padding. This implementation chooses a 4-connected cross neighborhood
     * (center, north, south, west, east) and treats pixels outside the image as
     * background. Thus, foreground pixels on an image edge are contour pixels.
     *
     * Input and output are assumed not to overlap; aliasing is not specified by
     * the contract.
     */
    for (y = 0; y < h; ++y) {
        for (x = 0; x < w; ++x) {
            int i = y * w + x;
            int eroded = 0;

            if (in[i] == 1.0 &&
                y > 0 && y + 1 < h &&
                x > 0 && x + 1 < w &&
                in[(y - 1) * w + x] == 1.0 &&
                in[(y + 1) * w + x] == 1.0 &&
                in[y * w + (x - 1)] == 1.0 &&
                in[y * w + (x + 1)] == 1.0) {
                eroded = 1;
            }

            out[i] = (in[i] == 1.0 && !eroded) ? 1.0 : 0.0;
        }
    }
}
