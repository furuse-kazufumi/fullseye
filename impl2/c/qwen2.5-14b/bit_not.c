void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない。入力画像の各ピクセルに対して 1 - x の計算を行う。
    // 画像の端の処理は不要であると判断。入力画像の範囲外の値が来ても、
    // その範囲外の値は考慮せず、与えられた範囲内の値に対してのみ処理を行う。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = 1.0 - in[idx];
        }
    }
}
