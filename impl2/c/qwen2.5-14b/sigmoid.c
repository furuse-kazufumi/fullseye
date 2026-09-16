void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b を使用してシグモイド関数のパラメータを計算
    double k = 4 + 12 * a;  // 傾き
    double x0 = 0.2 + 0.6 * b;  // 変曲点

    // 各ピクセルに対してシグモイド関数を適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double v = in[y * w + x];
            out[y * w + x] = 1.0 / (1.0 + exp(-k * (v - x0)));
        }
    }
}
