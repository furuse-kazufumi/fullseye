void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。仕様書に従い無視する。
    // 画像の端の処理については、仕様書が明示していないため、端の値をそのまま使用する。
    // a が指数 γ として使用される。γ の範囲は 0.5 から 2.0 まで。仕様書では 0.5 が既定値とされる。
    // 入力画像の値域は [0,1] と想定されるが、範囲外の値が来ても落ちないよう対応する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // 入力値が [0,1] の範囲外の場合、範囲内にクリップする。
            if (value < 0.0) {
                value = 0.0;
            } else if (value > 1.0) {
                value = 1.0;
            }
            // γ 乗を計算
            out[idx] = pow(value, a);
        }
    }
}
