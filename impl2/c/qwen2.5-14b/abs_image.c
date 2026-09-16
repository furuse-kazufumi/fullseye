void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用パラメータであるため、無視する。
    // 画像の各画素に対して絶対値を取る。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = fabs(in[idx]);  // 画素値の絶対値を計算
        }
    }
}
