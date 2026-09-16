void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この op は入力画像の形状と同じサイズの空 region を生成する。
    // つまり、出力はすべて 0.0 で初期化される。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }
}
