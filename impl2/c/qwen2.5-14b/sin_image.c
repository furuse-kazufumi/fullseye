void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b は未使用パラメータであるため、無視する。
    // 画像の各ピクセルに対して正弦関数を適用する。
    // 入力値は [0, 1] の範囲であると想定するが、範囲外の値も受け入れる。
    // 出力値も [0, 1] の範囲に収まるように調整する。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像のピクセルを取得
            double input = in[y * w + x];
            // 正弦関数を適用
            double output = (sin(2 * M_PI * input) + 1) / 2;
            // 出力画像に結果を格納
            out[y * w + x] = output;
        }
    }
}
