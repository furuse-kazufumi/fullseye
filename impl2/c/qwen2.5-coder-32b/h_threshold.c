void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 帯域しきい値処理: a < x < a + 0.5 + 0.5 * b を満たす画素を前景とする
    double lower_bound = a;
    double upper_bound = a + 0.5 + 0.5 * b;

    // 帯域幅が 0.5 を超えないように調整
    if (upper_bound > 1.0) {
        upper_bound = 1.0;
    }

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];
            if (pixel_value > lower_bound && pixel_value < upper_bound) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
