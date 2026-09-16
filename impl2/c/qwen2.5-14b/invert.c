void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。仕様書に従い、これらのパラメータは無視する。

    // 入力画像の各ピクセルに対して、1 - clip(v, 0, 1) を計算する。
    // これは、入力値が [0, 1] の範囲外にある場合でも、0 または 1 にクリップされる。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // クリッピング処理
            if (value < 0) {
                value = 0;
            } else if (value > 1) {
                value = 1;
            }
            // 1 - value を計算
            out[idx] = 1 - value;
        }
    }
}
