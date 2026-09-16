void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の処理については、境界値をそのまま使用する。
    // これは、仕様書で明示的に指定されていないため、実装者の判断による。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 出力画像の各ピクセルは入力画像の各ピクセルと同じ値を持つ。
            // これは、仕様書で a と b が使用されないことが明記されているため。
            out[y * w + x] = in[y * w + x];
        }
    }
}
