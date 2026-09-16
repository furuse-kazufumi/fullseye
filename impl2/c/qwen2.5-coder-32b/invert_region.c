void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用なので無視する。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            // 入力が 0.5 より大きい場合は領域に属するとして 1.0 にし、それ以外は 0.0 にする。
            out[index] = (in[index] > 0.5) ? 0.0 : 1.0;
        }
    }
}
