void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a はガンマ指数を 0.3 から 2.8 の範囲で調整するパラメータとして使用します。
    // b は未使用のパラメータです。
    // 入力画像の各ピクセルに対してガンマ補正を適用します。
    // 出力画像の値域は [0,1] に保たれます。

    double gamma = 0.3 + 2.5 * a;  // ガンマ指数の計算

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // 入力画像の値が [0,1] の範囲外の場合、範囲内にクリップします。
            if (value < 0.0) {
                value = 0.0;
            } else if (value > 1.0) {
                value = 1.0;
            }
            // ガンマ補正の適用
            out[idx] = pow(value, gamma);
        }
    }
}
