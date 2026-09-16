void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a を使用して有効ビット数を計算
    int bits = 1 + (int)(a * 6); // bits の範囲は 1 から 7 まで
    int mask = (1 << bits) - 1; // マスク生成

    // 入力画像を処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像のピクセルを取得
            double pixel = in[y * w + x];
            // 値域を [0, 255] に変換
            int scaled_pixel = (int)(pixel * 255);
            // ポスタライズ処理
            int posterized_pixel = scaled_pixel & mask;
            // 出力画像に書き込み
            out[y * w + x] = (double)posterized_pixel / 255.0;
        }
    }
}
