void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によれば、入力画像の内容は無視されるため、単に a の値を全画素に出力する。
    // b は未使用であるため、この関数では無視する。

    // 全画素に対して a の値を設定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = a;
        }
    }
}
