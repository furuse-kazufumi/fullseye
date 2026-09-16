void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用パラメータであるため、無視する。
    // 画像の各ピクセルに対して arccos(x) / π を計算する。
    // 範囲外の値が入力された場合、その値は [0, 1] の範囲にクリップされる。
    // これは仕様書で明示的に定義されていないため、この処理を追加する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // クリッピング
            if (value < 0.0) {
                value = 0.0;
            } else if (value > 1.0) {
                value = 1.0;
            }
            // arccos(x) / π の計算
            out[idx] = acos(value) / M_PI;
        }
    }
}
