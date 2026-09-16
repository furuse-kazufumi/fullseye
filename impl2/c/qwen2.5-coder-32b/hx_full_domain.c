void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この op は入力画像の形状と同じサイズの region を生成します。
    // region は画像の定義域全体を表すため、すべてのピクセルが 1.0 になります。
    // つまみ a, b は使用されません。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 1.0;
        }
    }
}
