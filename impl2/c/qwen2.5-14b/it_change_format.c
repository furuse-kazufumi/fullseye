void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は無視する。

    // 出力画像の高さと幅を決定
    int max_dim = (h > w) ? h : w;
    int out_h = max_dim;
    int out_w = max_dim;

    // 出力画像の初期化
    for (int y = 0; y < out_h; ++y) {
        for (int x = 0; x < out_w; ++x) {
            out[y * out_w + x] = 0.0; // 画像をゼロで初期化
        }
    }

    // 入力画像を出力画像にコピー
    // 入力画像が正方形の場合はそのままコピー
    if (h == w) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                out[y * out_w + x] = in[y * w + x];
            }
        }
    } else {
        // 入力画像が正方形でない場合、中央に配置してゼロパディング
        int pad_h = (max_dim - h) / 2;
        int pad_w = (max_dim - w) / 2;

        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                out[(y + pad_h) * out_w + (x + pad_w)] = in[y * w + x];
            }
        }
    }
}
