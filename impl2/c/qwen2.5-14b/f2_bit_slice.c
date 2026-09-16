void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0, 1] の範囲で、ビット平面の選択を示す。0 は LSB、1 は MSB に対応する。
    // 画像の各ピクセルは [0, 1] の範囲で与えられるが、範囲外の値も許容する。
    // 出力は {0, 1} のビット画像となる。

    // a を整数に変換し、ビット平面のインデックスとして使用
    int bit_plane = (int)(a * 8);  // 0 から 7 までの整数に変換

    // 入力画像を処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像のピクセルを 8 ビットに量子化
            int pixel = (int)(in[y * w + x] * 255);

            // 指定されたビット平面を取得
            int bit_value = (pixel >> bit_plane) & 1;

            // 出力画像に書き込み
            out[y * w + x] = bit_value;
        }
    }
}
