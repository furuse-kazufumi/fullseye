void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は出力を変えないため、この関数では無視する。
    // 画像の端は、画素値が [0,1] の範囲内にあると仮定し、範囲外の値は内部で適切に処理する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel_value = in[y * w + x];
            // 画素値が (a, a + 0.5 + 0.5b) の範囲内にある場合、前景として 1 を出力
            if (pixel_value >= a && pixel_value < a + 0.5) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
