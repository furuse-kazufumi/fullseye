void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、入力は二値の領域であり、0.0 または 1.0 のみが入力される。
    // 出力も同様に 0.0 または 1.0 のみを出力する。

    // つまみ a, b は使用しない。
    (void)a;
    (void)b;

    // 出力画像の各画素を設定
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の画素を取得
            double pixel = in[y * w + x];
            // 二値化: 0.0 または 1.0 に変換
            if (pixel == 0.0 || pixel == 1.0) {
                // 補集合: 1.0 から引く
                out[y * w + x] = (pixel == 1.0) ? 0.0 : 1.0;
            } else {
                // 入力が 0.0 または 1.0 以外の場合は、仕様書の範囲外の値として扱い、
                // 1.0 と見なし、0.0 に変換する。
                out[y * w + x] = 0.0;
            }
        }
    }
}
