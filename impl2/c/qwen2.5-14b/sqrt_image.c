void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。
    (void)a;
    (void)b;

    // 入力画像の各画素に対して平方根を計算し、出力画像に格納する。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の画素値を取得
            double input_value = in[y * w + x];
            // 画素値が 0 以上の場合、平方根を計算
            if (input_value >= 0) {
                out[y * w + x] = sqrt(input_value);
            } else {
                // 画素値が負の場合、0 に設定
                out[y * w + x] = 0.0;
            }
        }
    }
}
