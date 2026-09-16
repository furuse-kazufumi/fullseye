void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は使用しない。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (in[index] > a) {
                out[index] = a;
            } else {
                out[index] = in[index];
            }
        }
    }
}
