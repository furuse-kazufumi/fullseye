void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、つまみ a と b は出力を変更しないと明記されている。
    // したがって、この関数は入力画像をそのまま出力する。

    // 入力画像の各ピクセルを出力画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }
}
