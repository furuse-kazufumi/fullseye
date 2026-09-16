void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a はしきい値として使用され、b は無視される。
    // しきい値 a は [0, 1] の範囲で、入力画像の各ピクセルに対して適用される。
    // 出力画像は 0.0 (背景) または 1.0 (オブジェクト) のみを含む。

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の現在のピクセルの値を取得
            double pixel_value = in[y * w + x];

            // しきい値処理
            if (pixel_value >= a) {
                out[y * w + x] = 1.0; // オブジェクト
            } else {
                out[y * w + x] = 0.0; // 背景
            }
        }
    }
}
