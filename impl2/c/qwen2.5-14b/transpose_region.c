void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。
    (void)a;
    (void)b;

    // 転置後の画像の幅と高さを計算
    int out_h = w;
    int out_w = h;

    // 出力画像を初期化
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            out[y * out_w + x] = 0.0;
        }
    }

    // 入力画像を転置して出力画像に書き込む
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の (x, y) の画素を出力画像の (y, x) に転置
            out[y * out_w + x] = in[y * w + x];
        }
    }
}
