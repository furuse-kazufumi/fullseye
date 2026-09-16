void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を境界値を保持するように処理するためのパディング
    // 画像の端は境界値を保持するように処理する。境界値は入力画像の端の値を用いる。
    // これは、画像の端が境界値を保持するように処理するための一般的な手法である。

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 埋め込み処理
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            double min_val = in[(y - 1) * w + x - 1];
            min_val = fmin(min_val, in[(y - 1) * w + x]);
            min_val = fmin(min_val, in[(y - 1) * w + x + 1]);
            min_val = fmin(min_val, in[y * w + x - 1]);
            min_val = fmin(min_val, in[y * w + x]);
            min_val = fmin(min_val, in[y * w + x + 1]);
            min_val = fmin(min_val, in[(y + 1) * w + x - 1]);
            min_val = fmin(min_val, in[(y + 1) * w + x]);
            min_val = fmin(min_val, in[(y + 1) * w + x + 1]);

            // 埋め込み処理
            if (in[y * w + x] < min_val) {
                out[y * w + x] = fmin(in[y * w + x] + a * (min_val - in[y * w + x]), min_val);
            }
        }
    }
}
