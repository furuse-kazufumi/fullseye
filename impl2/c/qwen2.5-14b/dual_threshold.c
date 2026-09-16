void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は使用され、b は無視される。a の範囲は [0,1]。
    // 画像の端はそのまま処理する。境界外アクセスは行わない。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel = in[y * w + x];
            // 中央値 0.5 を「ゼロ」とみなし、|x - 0.5| > 0.1 + 0.35 * a を満たす画素を前景とする。
            if (fabs(pixel - 0.5) > (0.1 + 0.35 * a)) {
                out[y * w + x] = 1.0;
            } else {
                out[y * w + x] = 0.0;
            }
        }
    }
}
