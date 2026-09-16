void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a が下限しきい値、b が帯域幅。0.5 が固定の幅。
    // しきい値は a < x < a + 0.5 + 0.5*b を満たす画素を前景とする。
    // 画像の端は境界値を無視する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            double threshold_min = a;
            double threshold_max = a + 0.5 + 0.5 * b;

            // しきい値処理
            if (pixel > threshold_min && pixel < threshold_max) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
