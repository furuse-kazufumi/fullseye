void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、a と b は未使用なので無視する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            out[index] = 1.0 - in[index];
        }
    }
}
