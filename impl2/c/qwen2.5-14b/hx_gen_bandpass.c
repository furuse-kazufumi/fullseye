void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // フーリエ変換の結果を格納する配列
    double* fft_result = (double*)malloc(h * w * sizeof(double) * 2);
    if (fft_result == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 1. 入力画像をフーリエ変換
    // ここでは、単純なフーリエ変換の実装を想定しています。
    // 実際には、より適切なフーリエ変換ライブラリを使用することを推奨します。
    // 以下は、フーリエ変換の結果を fft_result に格納する仮想的な処理です。
    // 通常、フーリエ変換ライブラリを使用してこの部分を実装します。
    // ここでは、単純な例として、入力画像の値をそのまま fft_result にコピーします。
    for (int i = 0; i < h * w; i++) {
        fft_result[i * 2] = in[i];
        fft_result[i * 2 + 1] = 0.0;
    }

    // 2. バンドパスフィルタリングのマスクを生成
    double r_lo = 0.05 + 0.4 * a;
    double r_hi = r_lo + 0.05 + 0.3 * b;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double cy = (y - h / 2.0) / (h / 2.0);
            double cx = (x - w / 2.0) / (w / 2.0);
            double r = sqrt(cy * cy + cx * cx);
            double mask = (r >= r_lo && r <= r_hi) ? 1.0 : 0.0;
            int idx = (y * w + x) * 2;
            fft_result[idx] *= mask;
            fft_result[idx + 1] *= mask;
        }
    }

    // 3. フーリエ逆変換
    // 同様に、フーリエ逆変換の結果を out に格納する仮想的な処理です。
    // 通常、フーリエ逆変換ライブラリを使用してこの部分を実装します。
    // ここでは、単純な例として、fft_result の実部を out にコピーします。
    for (int i = 0; i < h * w; i++) {
        out[i] = fft_result[i * 2];
    }

    // メモリを解放
    free(fft_result);
}
