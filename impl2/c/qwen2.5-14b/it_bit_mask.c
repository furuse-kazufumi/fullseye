void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は [0,1] の範囲にクリップ
    double mask = (a < 0.0) ? 0.0 : (a > 1.0) ? 255.0 : a * 255.0;
    int mask_int = (int)mask;

    // 入力画像を 0-255 に量子化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int pixel = (int)(in[y * w + x] * 255.0);
            // 量子化されたピクセルとマスクとのビットアンド
            int result = pixel & mask_int;
            // 結果を [0,1] の範囲にスケーリング
            out[y * w + x] = result / 255.0;
        }
    }
}
