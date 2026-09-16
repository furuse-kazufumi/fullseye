void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a と b の範囲を [0,1] にクリップする
    double gain = (a < 0.0) ? 0.0 : ((a > 1.0) ? 1.0 : a);
    double offset = (b < 0.0) ? 0.0 : ((b > 1.0) ? 1.0 : b);

    // オフセットの中心値を 0.5 に合わせる
    offset = offset - 0.5;

    // 入力画像を線形変換し、出力画像に書き込む
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double v = in[y * w + x];
            double scaled = gain * v + offset;
            // 画像の値域を [0,1] にクリップ
            out[y * w + x] = (scaled < 0.0) ? 0.0 : ((scaled > 1.0) ? 1.0 : scaled);
        }
    }
}
