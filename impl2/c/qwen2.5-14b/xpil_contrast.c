void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 強調係数の計算
    double factor = 2 * a;
    double mean = 0.5; // 画像の平均輝度を0.5と仮定

    // 画像の各ピクセルに対して処理を行う
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double pixel = in[idx];

            // 範囲外の値を処理
            if (pixel < 0) {
                pixel = 0;
            } else if (pixel > 1) {
                pixel = 1;
            }

            // コントラスト調整の計算
            double adjusted = (pixel - mean) * factor + mean;

            // 範囲外の値を処理
            if (adjusted < 0) {
                adjusted = 0;
            } else if (adjusted > 1) {
                adjusted = 1;
            }

            // 出力画像に書き込み
            out[idx] = adjusted;
        }
    }
}
