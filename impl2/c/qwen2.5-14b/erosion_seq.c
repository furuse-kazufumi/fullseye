void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a は反復回数を決定するパラメータ。0.1 から 0.9 の範囲で、1 から 4 までの整数に丸められる。
    int iterations = (int)(a * 4 + 0.5); // 0.1 -> 1, 0.5 -> 2, 0.9 -> 4
    iterations = (iterations < 1) ? 1 : iterations; // 最小 1 回の反復

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 反復処理
    for (int i = 0; i < iterations; i++) {
        // 1 回の収縮処理
        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                // 十字形構造要素による収縮
                if (in[(y - 1) * w + x] == 1 &&
                    in[(y + 1) * w + x] == 1 &&
                    in[y * w + (x - 1)] == 1 &&
                    in[y * w + (x + 1)] == 1) {
                    out[y * w + x] = 1;
                } else {
                    out[y * w + x] = 0;
                }
            }
        }
        // 出力画像を入力画像にコピー
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                in[y * w + x] = out[y * w + x];
            }
        }
    }
}
