void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は無視する
    (void)a;
    (void)b;

    // 出力画像の最大値を求める
    double max_val = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            if (val > max_val) {
                max_val = val;
            }
        }
    }

    // 出力画像を計算し、最大値で正規化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            out[y * w + x] = val / max_val;
        }
    }
}
