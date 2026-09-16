void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。仕様書に従い無視する。
    // つまみ a の値域は [0,1]。gain の値域は [0.5, 2.0] に変換する。
    double gain = 0.5 + 1.5 * a;

    // 出力画像の各ピクセルに対して対数変換を適用する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double input = in[idx];
            // 対数変換の式: out = gain * log(1 + in)
            // ここで log は自然対数 (ln) を使用する。
            double output = gain * log(1 + input);
            // 出力を [0,1] の範囲にクリップする。
            out[idx] = output < 0 ? 0 : (output > 1 ? 1 : output);
        }
    }
}
