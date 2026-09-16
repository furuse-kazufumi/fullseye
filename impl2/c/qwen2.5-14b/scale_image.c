void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a の範囲は 0.5 から 2.0 まで、b の範囲は -0.5 から +0.5 までに変換
    double slope = 0.5 + 1.5 * a;  // 傾き (Mult 相当)
    double offset = b - 0.5;       // オフセット (Add 相当)

    // 出力画像の各ピクセルに対して線形変換を適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double value = in[idx];
            // 線形変換を適用し、結果を [0, 1] の範囲にクリップ
            out[idx] = (slope * value + offset < 0) ? 0 : (slope * value + offset > 1) ? 1 : slope * value + offset;
        }
    }
}
