void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the height and width of the rectangle
    int hh = (int)(h * (0.2 + 0.7 * a));
    int ww = (int)(w * (0.2 + 0.7 * b));

    // Calculate the top-left corner of the rectangle
    int top = (h - hh) / 2;
    int left = (w - ww) / 2;

    // Initialize the output region with 0.0
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // Set the rectangle region to 1.0
    for (int y = top; y < top + hh; y++) {
        for (int x = left; x < left + ww; x++) {
            out[y * w + x] = 1.0;
        }
    }
}
