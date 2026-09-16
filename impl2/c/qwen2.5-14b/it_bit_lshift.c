void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、7ビットのシフト量を決定する。a=0.5 は 3.5 で、これを 3 に丸める。
    int shift_amount = (int)round(a * 7.0);

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 入力画像のピクセルを取得
            double in_val = in[y * w + x];

            // 入力値を 0-255 の範囲に変換
            int in_val_int = (int)(in_val * 255.0);

            // 左シフト
            int shifted_val = in_val_int << shift_amount;

            // 8ビットに丸める (オーバーフローはラップアラウンド)
            shifted_val &= 0xFF;

            // 出力画像のピクセルに格納
            out[y * w + x] = (double)shifted_val / 255.0;
        }
    }
}
