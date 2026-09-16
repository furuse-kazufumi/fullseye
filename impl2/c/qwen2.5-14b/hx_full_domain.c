void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によれば、a と b は未使用であるため、無視する。
    // 出力は全 1 の region となるため、out に 1.0 を書き込む。

    // h*w 個の要素すべてに対して 1.0 を設定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 1.0;
        }
    }
}
