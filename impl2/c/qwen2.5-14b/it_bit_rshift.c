void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 仕様書によると、a が右シフトの量を決定し、b は無視される。
    // a の値域は [0,1] だが、右シフトの量は 0 から 7 までの整数である必要がある。
    // したがって、a を 0 から 7 までの整数に丸める。a が 0.1 から 0.9 の範囲で
    // 連続的に変化するとき、右シフトの量は 0 から 7 までの整数に連続的に変化する。
    // また、a が 0.1 から 0.9 の範囲で変化したとき、出力が変化しないという情報から、
    // a が 0.5 のとき、右シフトの量は 3 と仮定する。

    int shift_amount = (int)(a * 7 + 0.5); // 0.5 を加えて丸める

    // 画像の各ピクセルに対して右シフトを適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            double pixel_value = in[index];
            // 8ビット量子化
            int quantized_value = (int)(pixel_value * 255 + 0.5); // 0.5 を加えて丸める
            // 右シフト
            int shifted_value = quantized_value >> shift_amount;
            // 量子化後の値を出力に書き込む
            out[index] = (double)shifted_value / 255.0;
        }
    }
}
