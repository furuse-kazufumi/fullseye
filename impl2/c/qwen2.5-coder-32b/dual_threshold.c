void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用であるため、無視する。
    // つまみ a は除外帯域の半幅を制御する。
    // しきい値の計算: 中央値 0.5 から a によって制御される範囲外の画素を前景とする。
    double threshold = 0.1 + 0.35 * a;

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel_value = in[y * w + x];
            // |x - 0.5| > 0.1 + 0.35 * a を満たす画素を前景とみなす。
            if (fabs(pixel_value - 0.5) > threshold) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
