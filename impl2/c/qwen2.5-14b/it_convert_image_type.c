void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲で、出力の精度を制御します。b は無視されます。
    int L = 2 + (int)(a * 254); // L は出力の精度レベル。最小 2、最大 256。
    double step = 1.0 / (L - 1); // 出力の精度レベル間のステップ幅。
    double min_val = 0.0; // 出力の最小値。
    double max_val = 1.0; // 出力の最大値。

    // 出力画像の各ピクセルを処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double in_val = in[idx]; // 入力画像の現在のピクセル値を取得

            // 入力値を出力の精度レベルに丸める
            double out_val = min_val + (int)((in_val - min_val) / step) * step;

            // 出力画像の現在のピクセルに値を設定
            out[idx] = out_val;
        }
    }
}
