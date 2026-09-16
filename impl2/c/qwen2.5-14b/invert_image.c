void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。仕様書に従い、これらのパラメータは無視する。

    // 出力画像の各ピクセルを入力画像の各ピクセルから計算する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 画像のピクセル値を反転させる。
            out[y * w + x] = 1.0 - in[y * w + x];
        }
    }
}
