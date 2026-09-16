void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は使用しない
    (void)b;

    // しきい値 a で画像を二値化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = (in[idx] > a) ? 1.0 : 0.0;
        }
    }
}
