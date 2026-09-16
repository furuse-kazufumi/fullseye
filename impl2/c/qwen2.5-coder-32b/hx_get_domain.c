void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この op は入力画像の定義域を region として取得します。
    // 出力は入力画像と同じ形状の全 1 の float64 配列(region)です。
    // つまみ a, b は未使用です。

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 1.0;
        }
    }
}
