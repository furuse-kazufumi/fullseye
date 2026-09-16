void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は使用し、b は無視します。a は [0,1] の範囲で、画素値が a より大きい場合に a に丸められます。
    // 画像の端の処理は不要で、入力画像の各画素に対して処理が行われます。

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = (in[idx] > a) ? a : in[idx];
        }
    }
}
