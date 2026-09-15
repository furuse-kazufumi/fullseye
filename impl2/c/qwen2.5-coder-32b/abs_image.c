void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用なので無視する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            out[index] = (in[index] >= 0) ? in[index] : -in[index];
        }
    }
}
