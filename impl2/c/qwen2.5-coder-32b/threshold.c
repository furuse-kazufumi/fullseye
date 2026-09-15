void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、b は使用しない。
    // 画像の端の処理は特に指定がないため、単純にしきい値処理を行う。
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int index = y * w + x;
            out[index] = (in[index] > a) ? 1.0 : 0.0;
        }
    }
}
