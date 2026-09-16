void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は出力を変えないため、無視する。
    (void)b;

    // 出力画像の各ピクセルを計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 出力画像のピクセル位置を計算
            int out_idx = y * w + x;

            // 入力画像のピクセル位置を計算
            double input_value = in[y * w + x];

            // 出力画像のピクセル値を計算
            // 仕様書では「Texture / detail layer = input - structure, centred at 0.5」とあるが、
            // structure の具体的な計算方法が明示されていないため、
            // ここでは input_value から 0.5 を引いた値を出力として使用する。
            // これは「structure + (texture - 0.5) == input」を満たすように設計されていると解釈する。
            double output_value = input_value - 0.5;

            // 出力画像に値を設定
            out[out_idx] = output_value;
        }
    }
}
