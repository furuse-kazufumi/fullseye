void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は下限、a + 0.5 + 0.5b は上限となる。
    // 帯域しきい値の計算
    double lower_threshold = a;
    double upper_threshold = a + 0.5 + 0.5 * b;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];
            // 帯域しきい値内に収まる場合は前景(1.0)、それ以外は背景(0.0)
            if (pixel_value >= lower_threshold && pixel_value <= upper_threshold) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
