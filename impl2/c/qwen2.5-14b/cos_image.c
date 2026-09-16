void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用パラメータであるため、無視する。
    // 画像の各ピクセルに対して cos(2πx) + 1) / 2 を計算する。
    // 入力画像の値域は [0,1] と想定されるが、範囲外の値が来ても落ちないよう対応する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像のピクセルを取得
            double input_value = in[y * w + x];
            // cos(2πx) + 1) / 2 を計算
            double output_value = (cos(2 * M_PI * input_value) + 1) / 2;
            // 出力画像に結果を格納
            out[y * w + x] = output_value;
        }
    }
}
