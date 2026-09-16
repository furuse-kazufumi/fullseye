void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // しきい値の計算
    int threshold = 64 + 160 * a;

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double pixel_value = in[idx];

            // しきい値を超える画素値を反転
            if (pixel_value > threshold / 255.0) {
                out[idx] = 1.0 - pixel_value;
            } else {
                out[idx] = pixel_value;
            }
        }
    }
}
